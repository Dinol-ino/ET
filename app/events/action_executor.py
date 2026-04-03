from __future__ import annotations

import hashlib
import logging
from typing import Any

from app.core.utils import now_iso

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Executes or queues actions and captures outcome tracking hooks."""

    def __init__(self) -> None:
        self.action_log: list[dict[str, Any]] = []

    def execute(self, decision: dict[str, Any], event: dict[str, Any] | None = None) -> dict[str, Any]:
        event_payload = event or {}
        event_type = str(decision.get("event_type") or event_payload.get("event_type") or "")
        event_id = self._event_id(event_payload, event_type)
        agent = str(decision.get("agent") or "unknown_agent")
        priority = str(decision.get("priority") or "")
        action = decision.get("recommended_action")
        action_payload = action if isinstance(action, dict) else {}
        action_type = str(action_payload.get("type") or "")
        timing = str(action_payload.get("timing") or "")
        message = str(action_payload.get("message") or "")
        execution = decision.get("execution")
        execution_payload = execution if isinstance(execution, dict) else {}
        auto_execute = bool(execution_payload.get("auto_execute", False))
        requires_approval = bool(execution_payload.get("requires_approval", False))

        status = "executed" if auto_execute and not requires_approval else "pending"
        record = {
            "event_id": event_id,
            "event_type": event_type,
            "agent": agent,
            "action": {
                "type": action_type,
                "message": message,
                "timing": timing,
            },
            "status": status,
            "timestamp": now_iso(),
            "outcome": None,
        }
        self.action_log.append(record)

        logger.info(
            "action_execution event_id=%s event_type=%s agent=%s status=%s priority=%s action_type=%s timing=%s message=%s",
            event_id,
            event_type,
            agent,
            status,
            priority,
            action_type,
            timing,
            message,
        )

        return {
            "status": status,
            "event_id": event_id,
            "event_type": event_type,
            "agent": agent,
            "action_type": action_type,
            "timing": timing,
            "priority": priority,
            "requires_approval": requires_approval,
            "outcome": None,
        }

    def update_outcome(self, event_id: str, outcome: str) -> dict[str, Any] | None:
        """Placeholder hook for future post-action evaluation updates."""
        if outcome not in {"responded", "ignored", "converted"}:
            return None
        for record in reversed(self.action_log):
            if str(record.get("event_id")) == event_id:
                record["outcome"] = outcome
                return record
        return None

    @staticmethod
    def _event_id(event: dict[str, Any], event_type: str) -> str:
        data = event.get("data")
        data_dict = data if isinstance(data, dict) else {}
        entity_id = (
            data_dict.get("deal_id")
            or data_dict.get("contact_id")
            or data_dict.get("company_name")
            or "unknown_entity"
        )
        timestamp = str(event.get("timestamp") or "")
        raw = f"{event_type}:{entity_id}:{timestamp}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
