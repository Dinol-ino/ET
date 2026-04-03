from __future__ import annotations

from typing import Any

from app.agents.deterministic_engine import DeterministicDecisionEngine


class RetentionAgent:
    """Strict deterministic retention agent."""

    def __init__(self) -> None:
        self.engine = DeterministicDecisionEngine()

    def handle_event(
        self,
        event_data: dict[str, Any],
        crm_data: dict[str, Any],
        engagement_metrics: dict[str, Any],
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return self.engine.decide(
            agent_name="retention_agent",
            event_data=event_data,
            crm_data=crm_data,
            engagement_metrics=engagement_metrics,
            history=history,
        )
