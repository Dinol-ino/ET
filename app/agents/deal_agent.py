from __future__ import annotations


class DealAgent:
    """Placeholder agent interface for future deal-intelligence reasoning graphs."""

    def recommend_next_step(self, risk_score: int) -> str:
        if risk_score >= 70:
            return "Escalate to manager and re-engage stakeholders within 24 hours."
        if risk_score >= 40:
            return "Schedule a follow-up meeting and confirm decision timeline."
        return "Maintain cadence and monitor engagement signals."
