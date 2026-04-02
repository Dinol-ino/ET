from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import RiskLevel


@dataclass(slots=True)
class ProspectScoreResult:
    score: int
    reasons: list[str]


@dataclass(slots=True)
class DealRiskResult:
    risk_score: int
    risk_level: RiskLevel
    reasons: list[str]


@dataclass(slots=True)
class RetentionResult:
    churn_risk: bool
    reason: str | None


class ProspectScorer:
    def score(self, company_name: str, domain: str, industry: str | None, scraped_text: str) -> ProspectScoreResult:
        score = 40
        reasons: list[str] = []

        content_length = len(scraped_text or "")
        if content_length > 800:
            score += 20
            reasons.append("Rich website content available for qualification")
        elif content_length > 250:
            score += 10
            reasons.append("Moderate website presence")
        else:
            score -= 10
            reasons.append("Limited public data available")

        normalized_text = (scraped_text or "").lower()
        b2b_keywords = ["sales", "crm", "enterprise", "saas", "revenue", "pipeline"]
        if any(keyword in normalized_text for keyword in b2b_keywords):
            score += 20
            reasons.append("Strong B2B intent signals found")

        growth_keywords = ["scale", "expansion", "growth", "automation", "ai"]
        if any(keyword in normalized_text for keyword in growth_keywords):
            score += 10
            reasons.append("Growth-oriented messaging detected")

        if industry:
            score += 10
            reasons.append(f"Industry inferred as {industry}")

        if domain.endswith(".ai"):
            score += 5
            reasons.append("Domain suggests technology-first business")

        if company_name and len(company_name.split()) >= 2:
            score += 5
            reasons.append("Company identity appears established")

        return ProspectScoreResult(score=max(0, min(100, score)), reasons=reasons)


class DealRiskScorer:
    def score(self, inactivity_days: int, interaction_count: int, no_reply: bool) -> DealRiskResult:
        risk_score = 0
        reasons: list[str] = []

        if inactivity_days > 7:
            risk_score += 30
            reasons.append(f"Inactivity exceeds 7 days ({inactivity_days} days)")

        if no_reply:
            risk_score += 25
            reasons.append("No prospect replies detected")

        if interaction_count < 3:
            risk_score += 20
            reasons.append("Low interaction count on the deal")

        if inactivity_days > 21:
            risk_score += 15
            reasons.append("Extended inactivity period raises close risk")

        if interaction_count == 0:
            risk_score += 10
            reasons.append("No logged engagement activities")

        risk_score = max(0, min(100, risk_score))
        if risk_score >= 70:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 40:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        return DealRiskResult(risk_score=risk_score, risk_level=risk_level, reasons=reasons)


class RetentionScorer:
    def detect_churn(self, recent_count: int, prior_count: int) -> RetentionResult:
        if prior_count <= 0:
            return RetentionResult(churn_risk=False, reason=None)

        if recent_count == 0:
            return RetentionResult(churn_risk=True, reason="No recent engagement despite previous activity")

        drop_ratio = (prior_count - recent_count) / prior_count
        if prior_count >= 3 and drop_ratio >= 0.4:
            return RetentionResult(
                churn_risk=True,
                reason=f"Activity frequency dropped by {int(drop_ratio * 100)}% compared to prior period",
            )

        return RetentionResult(churn_risk=False, reason=None)
