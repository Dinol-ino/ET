from __future__ import annotations

import datetime as dt
import uuid

from app.core.utils import utcnow
from app.models.deal import Activity, Deal
from app.models.enums import ActivityDirection, ActivityType
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.contact_repository import ContactRepository
from app.repositories.deal_repository import DealRepository
from app.services.scoring import DealRiskScorer, RetentionScorer


class DealService:
    def __init__(
        self,
        deal_repo: DealRepository,
        analysis_repo: AnalysisRepository,
        contact_repo: ContactRepository,
        risk_scorer: DealRiskScorer,
        retention_scorer: RetentionScorer,
    ):
        self.deal_repo = deal_repo
        self.analysis_repo = analysis_repo
        self.contact_repo = contact_repo
        self.risk_scorer = risk_scorer
        self.retention_scorer = retention_scorer

    def analyze_deal(self, deal_id: uuid.UUID) -> dict[str, object]:
        deal = self.deal_repo.get_by_id(deal_id)
        if deal is None:
            raise ValueError(f"Deal {deal_id} not found")

        try:
            analysis_data = self._build_analysis_payload(deal)
            record = self.analysis_repo.create_deal_analysis(analysis_data)
            self.analysis_repo.db.commit()
        except Exception:
            self.analysis_repo.db.rollback()
            raise

        return self._serialize_analysis(record, deal)

    def analyze_all_deals(self) -> dict[str, object]:
        deals = self.deal_repo.list_all_deals()
        analyses: list[dict[str, object]] = []

        try:
            for deal in deals:
                payload = self._build_analysis_payload(deal)
                record = self.analysis_repo.create_deal_analysis(payload)
                analyses.append(self._serialize_analysis(record, deal))
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

        return {
            "deal_id": deal.id,
            "risk_score": risk.risk_score,
            "risk_level": risk.risk_level,
            "reasons": risk.reasons,
            "inactivity_days": inactivity_days,
            "interaction_count": interaction_count,
            "no_reply": no_reply,
            "churn_risk": retention.churn_risk,
            "churn_reason": retention.reason,
            "model_version": "deal_rule_v1",
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
    def _serialize_analysis(record, deal: Deal) -> dict[str, object]:
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
        }
