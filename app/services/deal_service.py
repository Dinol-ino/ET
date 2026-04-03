from __future__ import annotations

import datetime as dt
import uuid

from app.core.utils import utcnow
from app.events.action_executor import ActionExecutor
from app.events.event_generator import EventGenerator
from app.events.event_router import EventRouter
from app.models.deal import Activity, Deal
from app.models.enums import ActivityDirection, ActivityType
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.contact_repository import ContactRepository
from app.repositories.deal_repository import DealRepository
from app.services.scoring_engine import HybridScoringEngine
from app.services.scoring import DealRiskScorer, RetentionScorer


class DealService:
    PRIORITY_MAPPING = {"high": 3, "medium": 2, "low": 1}

    def __init__(
        self,
        deal_repo: DealRepository,
        analysis_repo: AnalysisRepository,
        contact_repo: ContactRepository,
        risk_scorer: DealRiskScorer,
        retention_scorer: RetentionScorer,
        scoring_engine: HybridScoringEngine | None = None,
        event_generator: EventGenerator | None = None,
        event_router: EventRouter | None = None,
        action_executor: ActionExecutor | None = None,
        dedup_window_hours: int = 12,
    ):
        self.deal_repo = deal_repo
        self.analysis_repo = analysis_repo
        self.contact_repo = contact_repo
        self.risk_scorer = risk_scorer
        self.retention_scorer = retention_scorer
        self.scoring_engine = scoring_engine or HybridScoringEngine()
        self.event_generator = event_generator
        self.event_router = event_router
        self.action_executor = action_executor
        self.dedup_window = dt.timedelta(hours=max(6, dedup_window_hours))
        self._recent_events: dict[tuple[str, str], dt.datetime] = {}

    def analyze_deal(self, deal_id: uuid.UUID) -> dict[str, object]:
        deal = self.deal_repo.get_by_id(deal_id)
        if deal is None:
            raise ValueError(f"Deal {deal_id} not found")

        try:
            analysis_data = self._build_analysis_payload(deal)
            event_results = analysis_data.pop("_event_results", [])
            score_components = analysis_data.pop("_score_components", {})
            record = self.analysis_repo.create_deal_analysis(analysis_data)
            self.analysis_repo.db.commit()
        except Exception:
            self.analysis_repo.db.rollback()
            raise

        return self._serialize_analysis(
            record,
            deal,
            event_results=event_results,
            score_components=score_components,
        )

    def analyze_all_deals(self) -> dict[str, object]:
        deals = self.deal_repo.list_all_deals()
        analyses: list[dict[str, object]] = []

        try:
            for deal in deals:
                payload = self._build_analysis_payload(deal)
                event_results = payload.pop("_event_results", [])
                score_components = payload.pop("_score_components", {})
                record = self.analysis_repo.create_deal_analysis(payload)
                analyses.append(
                    self._serialize_analysis(
                        record,
                        deal,
                        event_results=event_results,
                        score_components=score_components,
                    )
                )
            self.analysis_repo.db.commit()
        except Exception:
            self.analysis_repo.db.rollback()
            raise
        return {"total_deals": len(deals), "analyses": analyses}

    def get_dashboard_summary(self) -> dict[str, int]:
        return {
            "total_contacts": self.contact_repo.count(),
            "total_deals": self.deal_repo.count(),
            "prospects_analyzed": self.analysis_repo.count_prospect_analyses(),
            "deals_analyzed": self.analysis_repo.count_deals_analyzed(),
            "high_risk_deals": self.analysis_repo.count_high_risk_deals(),
            "potential_churn_deals": self.analysis_repo.count_churn_risk_deals(),
        }

    def _build_analysis_payload(self, deal: Deal) -> dict[str, object]:
        now = utcnow()
        activities = sorted(deal.activities, key=lambda item: item.occurred_at)

        last_activity_at = activities[-1].occurred_at if activities else deal.last_activity_at or deal.created_at
        if last_activity_at.tzinfo is None:
            last_activity_at = last_activity_at.replace(tzinfo=dt.timezone.utc)
        inactivity_days = max(0, (now - last_activity_at).days)
        interaction_count = len(activities)

        outbound_email_count = len(
            [
                activity
                for activity in activities
                if activity.activity_type == ActivityType.EMAIL
                and activity.direction == ActivityDirection.OUTBOUND
            ]
        )
        has_reply = any(
            activity.replied
            or (
                activity.activity_type == ActivityType.EMAIL
                and activity.direction == ActivityDirection.INBOUND
            )
            for activity in activities
        )
        no_reply = outbound_email_count > 0 and not has_reply

        risk = self.risk_scorer.score(
            inactivity_days=inactivity_days,
            interaction_count=interaction_count,
            no_reply=no_reply,
        )

        recent_count, prior_count = self._windowed_activity_counts(activities, now)
        retention = self.retention_scorer.detect_churn(recent_count=recent_count, prior_count=prior_count)

        event_results: list[dict[str, object]] = []
        if self.event_generator is not None and self.event_router is not None:
            events = self.event_generator.generate_for_deal(deal)
            crm_data = {
                "deal_id": str(deal.id),
                "deal_name": deal.name,
                "company_name": deal.contact.company_name if deal.contact else None,
                "risk_score": risk.risk_score,
                "stage": deal.stage,
            }
            engagement_metrics = {
                "inactivity_days": inactivity_days,
                "interaction_count": interaction_count,
                "recent_count": recent_count,
                "prior_count": prior_count,
                "last_activity_at": last_activity_at.isoformat(),
                "no_reply": no_reply,
            }
            event_candidates: list[dict[str, object]] = []
            history = self._build_history(activities)
            for event in events:
                if self.event_already_processed_recently(event):
                    continue
                decision = self.event_router.route_event(
                    event=event,
                    crm_data=crm_data,
                    engagement_metrics=engagement_metrics,
                    history=history,
                )
                event_candidates.append({"event": event, "decision": decision})

            event_candidates.sort(
                key=lambda item: self.PRIORITY_MAPPING.get(str(item["decision"].get("priority", "low")), 1),
                reverse=True,
            )
            llm_scores: list[int] = []
            for candidate in event_candidates:
                event = candidate["event"]
                decision = candidate["decision"]
                self._recent_events[self._event_key(event)] = utcnow()
                execution = (
                    self.action_executor.execute(decision, event=event.to_dict())
                    if self.action_executor is not None
                    else {"status": "skipped"}
                )
                event_results.append(
                    {
                        "event": event.to_dict(),
                        "decision": decision,
                        "execution": execution,
                    }
                )
                decision_text = str(decision.get("decision") or "").strip()
                if decision_text:
                    risk.reasons.append(f"Event {event.event_type}: {decision_text}")
                try:
                    llm_scores.append(int(decision.get("score") or 0))
                except (TypeError, ValueError):
                    pass

            llm_signal = max(llm_scores) if llm_scores else risk.risk_score
        else:
            llm_signal = risk.risk_score

        hybrid = self.scoring_engine.calculate(
            crm_data={
                "company_size": self._estimate_company_size(deal),
                "industry_fit": deal.stage in {"qualified", "proposal", "negotiation"},
                "industry": "General B2B",
            },
            engagement_metrics={
                "email_replies": 0 if no_reply else 1,
                "meetings_scheduled": 1 if interaction_count >= 3 else 0,
                "days_since_last_interaction": inactivity_days,
                "inactivity_days": inactivity_days,
            },
            llm_output={"score": llm_signal},
        )
        hybrid_risk = 100 - int(hybrid["final_score"])
        combined_risk_score = max(0, min(100, int(round((0.7 * risk.risk_score) + (0.3 * hybrid_risk)))))
        risk_level = self._risk_level_from_score(combined_risk_score)
        risk.reasons.append(str(hybrid["reasoning"]))

        return {
            "deal_id": deal.id,
            "risk_score": combined_risk_score,
            "risk_level": risk_level,
            "reasons": risk.reasons,
            "inactivity_days": inactivity_days,
            "interaction_count": interaction_count,
            "no_reply": no_reply,
            "churn_risk": retention.churn_risk,
            "churn_reason": retention.reason,
            "model_version": "deal_event_v2",
            "_event_results": event_results,
            "_score_components": hybrid["components"],
        }

    @staticmethod
    def _windowed_activity_counts(activities: list[Activity], now: dt.datetime) -> tuple[int, int]:
        recent_start = now - dt.timedelta(days=14)
        prior_start = now - dt.timedelta(days=28)

        recent_count = len(
            [
                activity
                for activity in activities
                if DealService._as_aware(activity.occurred_at) >= recent_start
            ]
        )
        prior_count = len(
            [
                activity
                for activity in activities
                if prior_start <= DealService._as_aware(activity.occurred_at) < recent_start
            ]
        )
        return recent_count, prior_count

    @staticmethod
    def _as_aware(value: dt.datetime) -> dt.datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=dt.timezone.utc)
        return value

    @staticmethod
    def _serialize_analysis(
        record,
        deal: Deal,
        event_results: list[dict[str, object]] | None = None,
        score_components: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return {
            "analysis_id": str(record.id),
            "deal_id": str(deal.id),
            "deal_name": deal.name,
            "risk_score": record.risk_score,
            "risk_level": record.risk_level.value,
            "reasons": record.reasons,
            "inactivity_days": record.inactivity_days,
            "interaction_count": record.interaction_count,
            "no_reply": record.no_reply,
            "churn_risk": record.churn_risk,
            "churn_reason": record.churn_reason,
            "created_at": record.created_at.isoformat(),
            "event_results": event_results or [],
            "score_components": score_components or {},
        }

    def event_already_processed_recently(self, event) -> bool:
        key = self._event_key(event)
        last_seen = self._recent_events.get(key)
        if last_seen is None:
            return False
        return (utcnow() - last_seen) <= self.dedup_window

    @staticmethod
    def _event_key(event) -> tuple[str, str]:
        data = event.data
        entity_id = data.get("deal_id") or data.get("contact_id") or data.get("company_name") or "unknown_entity"
        return (event.event_type, str(entity_id))

    @staticmethod
    def _estimate_company_size(deal: Deal) -> int:
        amount = float(deal.amount) if deal.amount is not None else 0.0
        if amount >= 100000:
            return 1000
        if amount >= 50000:
            return 500
        if amount >= 20000:
            return 200
        if amount > 0:
            return 50
        return 25

    @staticmethod
    def _risk_level_from_score(score: int):
        from app.models.enums import RiskLevel

        if score >= 70:
            return RiskLevel.HIGH
        if score >= 40:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    @staticmethod
    def _build_history(activities: list[Activity]) -> list[dict[str, object]]:
        history: list[dict[str, object]] = []
        tail = sorted(activities, key=lambda item: item.occurred_at, reverse=True)[:5]
        for activity in tail:
            history.append(
                {
                    "type": activity.activity_type.value,
                    "direction": activity.direction.value,
                    "replied": activity.replied,
                    "occurred_at": activity.occurred_at.isoformat(),
                    "subject": activity.subject,
                }
            )
        return history
