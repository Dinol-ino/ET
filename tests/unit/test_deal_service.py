import datetime as dt
import unittest

from app.db.base import Base
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.contact_repository import ContactRepository
from app.repositories.deal_repository import DealRepository
from app.services.deal_service import DealService
from app.services.scoring import DealRiskScorer, RetentionScorer
from tests.test_harness import TestAppFactory


class DealServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.factory = TestAppFactory()
        Base.metadata.create_all(bind=self.factory.engine)
        self.db = self.factory.SessionLocal()

    def tearDown(self) -> None:
        self.db.close()
        self.factory.cleanup()

    def test_deal_service_analyze_deal(self) -> None:
        contact_repo = ContactRepository(self.db)
        deal_repo = DealRepository(self.db)
        analysis_repo = AnalysisRepository(self.db)

        contact = contact_repo.upsert_contact(
            {
                "external_id": "c-unit-1",
                "email": "owner@contoso.com",
                "first_name": "Taylor",
                "last_name": "Ray",
            }
        )

        now = dt.datetime.now(tz=dt.timezone.utc)
        deal = deal_repo.upsert_deal(
            {
                "external_id": "d-unit-1",
                "name": "Contoso Pilot",
                "amount": "14000",
                "stage": "proposal",
                "last_activity_at": (now - dt.timedelta(days=12)).isoformat(),
            },
            contact_id=contact.id,
        )
        deal_repo.replace_activities(
            deal,
            [
                {
                    "activity_type": "EMAIL",
                    "direction": "OUTBOUND",
                    "subject": "Pilot follow-up",
                    "occurred_at": (now - dt.timedelta(days=12)).isoformat(),
                    "replied": False,
                }
            ],
        )
        self.db.commit()

        service = DealService(
            deal_repo=deal_repo,
            analysis_repo=analysis_repo,
            contact_repo=contact_repo,
            risk_scorer=DealRiskScorer(),
            retention_scorer=RetentionScorer(),
        )

        result = service.analyze_deal(deal.id)

        self.assertEqual(result["deal_id"], str(deal.id))
        self.assertGreaterEqual(result["risk_score"], 60)
        self.assertEqual(result["risk_level"], "MEDIUM")
        self.assertTrue(result["no_reply"])


if __name__ == "__main__":
    unittest.main()
