import unittest

from app.models.enums import RiskLevel
from app.services.scoring import DealRiskScorer, ProspectScorer, RetentionScorer


class ScoringTests(unittest.TestCase):
    def test_deal_risk_scorer_high_risk_rule_bundle(self) -> None:
        scorer = DealRiskScorer()

        result = scorer.score(inactivity_days=12, interaction_count=1, no_reply=True)

        self.assertGreaterEqual(result.risk_score, 75)
        self.assertEqual(result.risk_level, RiskLevel.HIGH)
        self.assertTrue(any("Inactivity exceeds 7 days" in reason for reason in result.reasons))
        self.assertTrue(any("No prospect replies" in reason for reason in result.reasons))
        self.assertTrue(any("Low interaction count" in reason for reason in result.reasons))

    def test_retention_scorer_flags_drop(self) -> None:
        scorer = RetentionScorer()

        result = scorer.detect_churn(recent_count=1, prior_count=4)

        self.assertTrue(result.churn_risk)
        self.assertIsNotNone(result.reason)

    def test_prospect_scorer_produces_bounded_score(self) -> None:
        scorer = ProspectScorer()

        result = scorer.score(
            company_name="Acme AI",
            domain="acme.ai",
            industry="SaaS",
            scraped_text="enterprise sales crm platform for revenue growth and automation",
        )

        self.assertGreaterEqual(result.score, 0)
        self.assertLessEqual(result.score, 100)
        self.assertGreaterEqual(result.score, 70)
        self.assertGreater(len(result.reasons), 0)


if __name__ == "__main__":
    unittest.main()
