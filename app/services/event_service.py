from __future__ import annotations

import datetime as dt
from typing import Any

from app.core.utils import utcnow
from app.events.action_executor import ActionExecutor
from app.events.event_generator import EventGenerator
from app.events.event_router import EventRouter
from app.events.event_schema import EventPayload
from app.repositories.deal_repository import DealRepository


class EventService:
    PRIORITY_MAPPING = {"high": 3, "medium": 2, "low": 1}

    def __init__(
        self,
        deal_repo: DealRepository,
        event_generator: EventGenerator,
        event_router: EventRouter,
        action_executor: ActionExecutor,
        dedup_window_hours: int = 12,
    ) -> None:
        self.deal_repo = deal_repo
        self.event_generator = event_generator
        self.event_router = event_router
        self.action_executor = action_executor
        self.dedup_window = dt.timedelta(hours=max(1, dedup_window_hours))
        self._recent_events: dict[tuple[str, str], dt.datetime] = {}

    def process_events(self, events: list[Any] | None = None, limit: int = 100) -> dict[str, Any]:
        return self.process_pending_events(limit=limit, request_events=events)

    def process_pending_events(self, limit: int = 100, request_events: list[Any] | None = None) -> dict[str, Any]:
        print("Using input events OR generator?")
        request_events = request_events or []
        if request_events:
            events = self._parse_request_events(request_events)
        else:
            events = self._generate_events(limit=limit)
        print("Events to process:", [event.to_dict() for event in events])

        filtered_events: list[EventPayload] = []
        for event in events:
            if self.event_already_processed_recently(event):
                continue
            filtered_events.append(event)
        print("Events after dedup:", [event.to_dict() for event in filtered_events])

        candidates: list[dict[str, Any]] = []
        for event in filtered_events:
            candidate = self._build_candidate(event)
            candidates.append(candidate)

        ordered = sorted(
            candidates,
            key=lambda item: self.PRIORITY_MAPPING.get(str(item["decision"].get("priority", "low")), 1),
            reverse=True,
        )

        processed_events: list[dict[str, Any]] = []
        for item in ordered:
            event = item["event"]
            print("Routing event:", event.to_dict())
            event_key = self._event_key(event)
            self._recent_events[event_key] = utcnow()
            execution = self.action_executor.execute(item["decision"], event=event.to_dict())
            result = {
                "event": event.to_dict(),
                "decision": item["decision"],
                "execution": execution,
            }
            print("Agent output:", result)
            processed_events.append(
                {
                    "event": result["event"],
                    "decision": result["decision"],
                    "execution": result["execution"],
                }
            )
        return {
            "processed_count": len(processed_events),
            "events": processed_events,
        }

    def process_event(
        self,
        event: EventPayload,
        crm_data: dict[str, Any],
        engagement_metrics: dict[str, Any],
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        decision = self.event_router.route_event(event, crm_data, engagement_metrics, history=history)
        execution = self.action_executor.execute(decision, event=event.to_dict())
        return {
            "event": event.to_dict(),
            "decision": decision,
            "execution": execution,
        }

    def _build_candidate(self, event: EventPayload) -> dict[str, Any]:
        data = event.data
        crm_data = {
            "company_name": data.get("company_name"),
            "deal_id": data.get("deal_id"),
            "deal_name": data.get("deal_name"),
            "stage": data.get("stage"),
            "risk_score": self._risk_score_from_event(data),
        }
        engagement_metrics = {
            "inactivity_days": int(data.get("inactivity_days") or 0),
            "interaction_count": int(data.get("interaction_count") or 0),
            "recent_count": int(data.get("recent_count") or 0),
            "prior_count": int(data.get("prior_count") or 0),
            "last_activity_at": data.get("last_activity_at"),
        }
        history = self._build_history(data)
        decision = self.event_router.route_event(
            event=event,
            crm_data=crm_data,
            engagement_metrics=engagement_metrics,
            history=history,
        )
        return {"event": event, "decision": decision}

    def event_already_processed_recently(self, event: EventPayload) -> bool:
        return False

    @staticmethod
    def _risk_score_from_event(data: dict[str, object]) -> int:
        inactivity = int(data.get("inactivity_days") or 0)
        interactions = int(data.get("interaction_count") or 0)
        score = 0
        if inactivity > 7:
            score += 30
        if inactivity > 14:
            score += 30
        if interactions < 3:
            score += 20
        if interactions == 0:
            score += 20
        return max(0, min(100, score))

    @staticmethod
    def _build_history(data: dict[str, object]) -> list[dict[str, Any]]:
        last_interactions = data.get("last_interactions")
        if isinstance(last_interactions, list):
            normalized = [item for item in last_interactions if isinstance(item, dict)]
            if normalized:
                return normalized

        history: list[dict[str, Any]] = []
        if data.get("last_activity_at"):
            history.append(
                {
                    "interaction": "last_activity",
                    "timestamp": data.get("last_activity_at"),
                    "summary": f"Recent interactions={data.get('recent_count', 0)}",
                }
            )
        return history

    @staticmethod
    def _event_key(event: EventPayload) -> tuple[str, str]:
        data = event.data
        entity_id = (
            data.get("deal_id")
            or data.get("contact_id")
            or data.get("company_name")
            or "unknown_entity"
        )
        return (event.event_type, str(entity_id))

    def _generate_events(self, limit: int) -> list[EventPayload]:
        deals = self.deal_repo.list_deals(limit=limit, offset=0)
        return self.event_generator.generate_from_deals(deals)

    @staticmethod
    def _parse_request_events(request_events: list[Any]) -> list[EventPayload]:
        parsed: list[EventPayload] = []
        for item in request_events:
            payload = item.model_dump() if hasattr(item, "model_dump") else dict(item)
            event_type = str(payload.get("event_type") or "").strip().lower()
            timestamp = str(payload.get("timestamp") or "").strip()
            data = payload.get("data")
            if not event_type or not timestamp or not isinstance(data, dict):
                continue
            if event_type not in {"new_lead", "engagement_drop", "deal_stagnant"}:
                # Keep invalid event_types visible in logs but avoid crashing.
                print("Skipping invalid event_type:", event_type)
                continue
            parsed.append(
                EventPayload(
                    event_type=event_type,  # type: ignore[arg-type]
                    timestamp=timestamp,
                    data=data,
                )
            )
        return parsed
