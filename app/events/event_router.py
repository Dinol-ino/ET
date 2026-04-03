from __future__ import annotations

from typing import Any

from app.agents.deal_agent import DealAgent
from app.agents.prospect_agent import ProspectAgent
from app.agents.retention_agent import RetentionAgent
from app.events.event_schema import EventPayload


class EventRouter:
    """Routes domain events to the appropriate agent and normalizes strict JSON output."""

    def __init__(
        self,
        prospect_agent: ProspectAgent | None = None,
        deal_agent: DealAgent | None = None,
        retention_agent: RetentionAgent | None = None,
    ) -> None:
        self.prospect_agent = prospect_agent or ProspectAgent()
        self.deal_agent = deal_agent or DealAgent()
        self.retention_agent = retention_agent or RetentionAgent()

    def route_event(
        self,
        event: EventPayload | dict[str, Any],
        crm_data: dict[str, Any],
        engagement_metrics: dict[str, Any],
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        event_data = event.to_dict() if isinstance(event, EventPayload) else dict(event)
        event_type = str(event_data.get("event_type") or "").strip().lower()
        print("Routing to agent:", event_type)
        agent_name = "retention_agent"

        if event_type == "new_lead":
            agent_name = "prospect_agent"
            result = self.prospect_agent.handle_event(event_data, crm_data, engagement_metrics, history=history)
        elif event_type == "deal_stagnant":
            agent_name = "deal_agent"
            result = self.deal_agent.handle_event(event_data, crm_data, engagement_metrics, history=history)
        elif event_type == "engagement_drop":
            agent_name = "retention_agent"
            result = self.retention_agent.handle_event(event_data, crm_data, engagement_metrics, history=history)
        else:
            result = self._fallback_unknown(event_data)

        return self._coerce_strict_json(event_type or "engagement_drop", result, agent_name=agent_name)

    @staticmethod
    def _fallback_unknown(event_data: dict[str, Any]) -> dict[str, Any]:
        event_type = str(event_data.get("event_type") or "engagement_drop")
        return {
            "event_type": event_type,
            "priority": "low",
            "signals_detected": ["Unsupported event type"],
            "decision": "No automated decision could be made for this event type.",
            "score": 20,
            "recommended_action": {
                "type": "email",
                "message": "Queue event for manual review and classify signal before next touchpoint.",
                "timing": "3 days",
            },
            "confidence": "low",
            "execution": {
                "auto_execute": False,
                "requires_approval": True,
            },
        }

    @staticmethod
    def _coerce_strict_json(event_type: str, result: dict[str, Any], agent_name: str) -> dict[str, Any]:
        priority = str(result.get("priority") or "medium").lower()
        if priority not in {"high", "medium", "low"}:
            priority = "medium"

        confidence = str(result.get("confidence") or "medium").lower()
        if confidence not in {"high", "medium", "low"}:
            confidence = "medium"

        score = EventRouter._safe_score(result.get("score"), default=50)

        action = result.get("recommended_action")
        action_dict = action if isinstance(action, dict) else {}
        action_type = str(action_dict.get("type") or "email").lower()
        if action_type not in {"email", "call", "escalate"}:
            action_type = "email"
        timing = str(action_dict.get("timing") or "24h").lower()
        if timing not in {"immediate", "24h", "3 days"}:
            timing = "24h"

        signals = result.get("signals_detected")
        signal_list = [str(item).strip() for item in signals] if isinstance(signals, list) else []
        signal_list = [item for item in signal_list if item]

        execution = result.get("execution")
        execution_dict = execution if isinstance(execution, dict) else {}
        requires_approval = bool(execution_dict.get("requires_approval", False))
        auto_execute = bool(execution_dict.get("auto_execute", False))

        if confidence == "low":
            requires_approval = True
            auto_execute = False
        if priority == "high" and confidence == "high":
            auto_execute = True
            requires_approval = False

        return {
            "event_type": event_type,
            "agent": agent_name,
            "priority": priority,
            "signals_detected": signal_list,
            "decision": str(result.get("decision") or "").strip(),
            "score": score,
            "recommended_action": {
                "type": action_type,
                "message": str(action_dict.get("message") or "").strip(),
                "timing": timing,
            },
            "confidence": confidence,
            "execution": {
                "auto_execute": auto_execute,
                "requires_approval": requires_approval,
            },
        }

    @staticmethod
    def _safe_score(value: Any, default: int) -> int:
        try:
            score = int(value)
        except (TypeError, ValueError):
            score = default
        return max(0, min(100, score))
