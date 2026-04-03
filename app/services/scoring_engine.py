from __future__ import annotations

from typing import Any


class HybridScoringEngine:
    """Deterministic hybrid scoring that combines rules, LLM signal, and engagement quality."""

    def calculate(
        self,
        crm_data: dict[str, Any] | None,
        engagement_metrics: dict[str, Any] | None,
        llm_output: dict[str, Any] | None,
    ) -> dict[str, Any]:
        crm = crm_data or {}
        engagement = engagement_metrics or {}
        llm = llm_output or {}

        rule_score = self._rule_score(crm, engagement)
        engagement_score = self._engagement_score(engagement)
        llm_score = self._llm_score(llm)

        final_score = int(round((0.4 * rule_score) + (0.4 * llm_score) + (0.2 * engagement_score)))
        final_score = self._clamp(final_score)

        reasoning = (
            f"Hybrid score combines rule={rule_score}, llm={llm_score}, engagement={engagement_score} "
            f"with weights 0.4/0.4/0.2 to produce final={final_score}."
        )

        return {
            "final_score": final_score,
            "components": {
                "rule_score": rule_score,
                "llm_score": llm_score,
                "engagement_score": engagement_score,
            },
            "reasoning": reasoning,
        }

    def _rule_score(self, crm_data: dict[str, Any], engagement_metrics: dict[str, Any]) -> int:
        size_signal = self._company_size_score(crm_data.get("company_size"))
        industry_signal = self._industry_fit_score(crm_data.get("industry_fit"), crm_data.get("industry"))
        days = self._to_int(
            engagement_metrics.get("days_since_last_interaction", engagement_metrics.get("inactivity_days")),
            default=30,
        )
        recency_signal = self._clamp(100 - (max(days, 0) * 4))

        score = int(round((0.35 * size_signal) + (0.35 * industry_signal) + (0.30 * recency_signal)))
        return self._clamp(score)

    def _engagement_score(self, engagement_metrics: dict[str, Any]) -> int:
        replies = self._to_int(engagement_metrics.get("email_replies"), default=0)
        meetings = self._to_int(engagement_metrics.get("meetings_scheduled"), default=0)
        days = self._to_int(
            engagement_metrics.get("days_since_last_interaction", engagement_metrics.get("inactivity_days")),
            default=30,
        )

        reply_component = self._clamp(replies * 30)
        meeting_component = self._clamp(meetings * 25)
        recency_component = self._clamp(100 - (max(days, 0) * 5))

        score = int(round((0.4 * reply_component) + (0.3 * meeting_component) + (0.3 * recency_component)))
        return self._clamp(score)

    def _llm_score(self, llm_output: dict[str, Any]) -> int:
        return self._clamp(self._to_int(llm_output.get("score"), default=50))

    def _company_size_score(self, value: Any) -> int:
        size = self._to_int(value, default=-1)
        if size < 0:
            return 50
        if size >= 1000:
            return 95
        if size >= 500:
            return 85
        if size >= 200:
            return 75
        if size >= 50:
            return 60
        if size >= 10:
            return 45
        return 30

    def _industry_fit_score(self, fit_value: Any, industry_value: Any) -> int:
        if isinstance(fit_value, bool):
            return 90 if fit_value else 35

        fit_int = self._to_int(fit_value, default=-1)
        if fit_int >= 0:
            return self._clamp(fit_int)

        industry = str(industry_value or "").strip().lower()
        if not industry:
            return 50
        strong_fit = {"saas", "fintech", "healthtech", "e-commerce", "consulting", "general b2b"}
        return 85 if industry in strong_fit else 55

    @staticmethod
    def _to_int(value: Any, default: int = 0) -> int:
        if value is None:
            return default
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        text = str(value).strip()
        if not text:
            return default
        digits = "".join(ch for ch in text if ch.isdigit() or ch == "-")
        try:
            return int(digits) if digits else default
        except ValueError:
            return default

    @staticmethod
    def _clamp(value: int) -> int:
        return max(0, min(100, int(value)))
