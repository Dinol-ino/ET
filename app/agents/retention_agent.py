from __future__ import annotations


class RetentionAgent:
    """Placeholder agent interface for future churn and retention strategy orchestration."""

    def recommend_playbook(self, churn_risk: bool) -> str:
        if churn_risk:
            return "Trigger retention playbook: executive check-in, usage review, and success plan."
        return "Account engagement is stable; continue standard customer success cadence."
