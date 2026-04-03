from __future__ import annotations

from typing import Any


class DeterministicDecisionEngine:
    """Strict rule-driven decision engine shared across prospect/deal/retention agents."""

    def decide(
        self,
        *,
        agent_name: str,
        event_data: dict[str, Any],
        crm_data: dict[str, Any],
        engagement_metrics: dict[str, Any],
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        event_type = str(event_data.get("event_type") or "").strip() or "insufficient data"

        days_inactive, has_days_inactive = self._as_int_with_presence(
            engagement_metrics, ["days_inactive", "inactivity_days"]
        )
        employees, has_employees = self._as_int_with_presence(crm_data, ["employees", "company_size"])
        engagement_score, has_engagement_score = self._as_int_with_presence(
            engagement_metrics, ["engagement_score", "score"]
        )

        signals: list[str] = []
        if has_days_inactive:
            signals.append(f"{days_inactive} days inactive")
        else:
            signals.append("insufficient data: days_inactive missing")

        if has_employees:
            signals.append(f"{employees} employees")
        else:
            signals.append("insufficient data: employees missing")

        if has_engagement_score:
            signals.append(f"engagement score {engagement_score}")
        else:
            signals.append("insufficient data: engagement_score missing")

        if history:
            signals.append(f"history records {len(history)}")

        risk_level = self._risk_level(days_inactive, has_days_inactive)
        strong_company = has_employees and employees >= 200
        high_intent = has_engagement_score and engagement_score >= 70
        low_intent = has_engagement_score and engagement_score < 30

        if risk_level == "high" or (strong_company and high_intent):
            priority = "high"
        elif risk_level == "medium":
            priority = "medium"
        else:
            priority = "low"

        score = 50
        if risk_level == "high":
            score -= 25
        elif risk_level == "medium":
            score -= 10
        if high_intent:
            score += 20
        if low_intent:
            score -= 15
        if strong_company:
            score += 15
        score = max(0, min(100, score))

        confidence = self._confidence(
            has_days_inactive=has_days_inactive,
            has_employees=has_employees,
            has_engagement_score=has_engagement_score,
        )
        auto_execute = priority == "high" and confidence == "high"
        requires_approval = confidence == "low"

        decision = self._decision_text(
            risk_level=risk_level,
            strong_company=strong_company,
            high_intent=high_intent,
            low_intent=low_intent,
            has_days_inactive=has_days_inactive,
            has_employees=has_employees,
            has_engagement_score=has_engagement_score,
            days_inactive=days_inactive,
            employees=employees,
            engagement_score=engagement_score,
            priority=priority,
        )

        recommended_action = self._recommended_action(
            agent_name=agent_name,
            event_type=event_type,
            priority=priority,
            confidence=confidence,
            crm_data=crm_data,
        )

        return {
            "event_type": event_type,
            "priority": priority,
            "signals_detected": signals,
            "decision": decision,
            "score": score,
            "recommended_action": recommended_action,
            "confidence": confidence,
            "execution": {
                "auto_execute": auto_execute,
                "requires_approval": requires_approval,
            },
        }

    @staticmethod
    def _as_int_with_presence(source: dict[str, Any], keys: list[str]) -> tuple[int, bool]:
        for key in keys:
            if key not in source:
                continue
            value = source.get(key)
            if value is None:
                return 0, False
            if isinstance(value, bool):
                return int(value), True
            if isinstance(value, (int, float)):
                return int(value), True
            text = str(value).strip()
            if not text:
                return 0, False
            try:
                return int(float(text)), True
            except ValueError:
                return 0, False
        return 0, False

    @staticmethod
    def _risk_level(days_inactive: int, has_days_inactive: bool) -> str:
        if not has_days_inactive:
            return "insufficient data"
        if days_inactive >= 14:
            return "high"
        if 7 <= days_inactive <= 13:
            return "medium"
        return "low"

    @staticmethod
    def _confidence(*, has_days_inactive: bool, has_employees: bool, has_engagement_score: bool) -> str:
        if has_days_inactive and has_employees and has_engagement_score:
            return "high"
        if not has_days_inactive:
            return "low"
        if not has_employees and not has_engagement_score:
            return "low"
        return "medium"

    @staticmethod
    def _decision_text(
        *,
        risk_level: str,
        strong_company: bool,
        high_intent: bool,
        low_intent: bool,
        has_days_inactive: bool,
        has_employees: bool,
        has_engagement_score: bool,
        days_inactive: int,
        employees: int,
        engagement_score: int,
        priority: str,
    ) -> str:
        reasons: list[str] = []
        if has_days_inactive:
            reasons.append(f"{days_inactive} days inactive -> {risk_level} risk")
        else:
            reasons.append("insufficient data: days_inactive missing")
        if has_employees:
            reasons.append(f"{employees} employees -> strong_company={str(strong_company).lower()}")
        else:
            reasons.append("insufficient data: employees missing")
        if has_engagement_score:
            reasons.append(
                f"engagement_score={engagement_score} -> high_intent={str(high_intent).lower()}, low_intent={str(low_intent).lower()}"
            )
        else:
            reasons.append("insufficient data: engagement_score missing")
        reasons.append(f"priority={priority}")
        return "; ".join(reasons)

    @staticmethod
    def _recommended_action(
        *,
        agent_name: str,
        event_type: str,
        priority: str,
        confidence: str,
        crm_data: dict[str, Any],
    ) -> dict[str, str]:
        company = str(crm_data.get("company_name") or "account").strip() or "account"
        if priority == "high":
            if agent_name == "deal_agent":
                action_type = "escalate"
                message = (
                    f"{company}: high-priority deal intervention required now. "
                    "Escalate owner and run immediate stakeholder recovery call."
                )
            elif agent_name == "retention_agent":
                action_type = "call"
                message = (
                    f"{company}: high-priority retention risk detected. "
                    "Call immediately to recover engagement and confirm blockers."
                )
            else:
                action_type = "call"
                message = (
                    f"{company}: high-priority prospect signal. "
                    "Call immediately to qualify timeline and decision owners."
                )
            return {"type": action_type, "message": message, "timing": "immediate"}

        if priority == "medium":
            if agent_name == "deal_agent":
                action_type = "call"
            else:
                action_type = "email"
            message = (
                f"{company}: medium-priority {event_type} signal. "
                "Send follow-up and schedule next action within 24-48 hours."
            )
            return {"type": action_type, "message": message, "timing": "24h"}

        message = (
            f"{company}: low-priority {event_type} signal. "
            "Place in nurture flow and recheck engagement in 3 days."
        )
        if confidence == "low":
            message = f"{message} insufficient data"
        return {"type": "email", "message": message, "timing": "3 days"}
