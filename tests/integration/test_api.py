import unittest

from tests.test_harness import TestAppFactory


class APITests(unittest.TestCase):
    def setUp(self) -> None:
        self.factory = TestAppFactory()
        self.client = self.factory.build_client()

    def tearDown(self) -> None:
        self.client.close()
        self.factory.cleanup()

    def test_full_api_flow(self) -> None:
        contacts_res = self.client.post("/api/hubspot/sync-contacts", json={"limit": 10})
        self.assertEqual(contacts_res.status_code, 200)
        contacts_data = contacts_res.json()
        self.assertEqual(contacts_data["status"], "success")
        self.assertEqual(contacts_data["data"]["synced_count"], 1)

        deals_res = self.client.post("/api/hubspot/sync-deals", json={"limit": 10})
        self.assertEqual(deals_res.status_code, 200)
        deals_data = deals_res.json()
        self.assertEqual(deals_data["status"], "success")
        self.assertEqual(deals_data["data"]["synced_count"], 1)

        analyze_all_res = self.client.post("/api/deal/analyze-all")
        self.assertEqual(analyze_all_res.status_code, 200)
        analyze_all_data = analyze_all_res.json()
        self.assertEqual(analyze_all_data["status"], "success")
        self.assertGreaterEqual(analyze_all_data["data"]["total_deals"], 1)

        summary_res = self.client.get("/api/dashboard/summary")
        self.assertEqual(summary_res.status_code, 200)
        summary_data = summary_res.json()
        self.assertEqual(summary_data["status"], "success")
        self.assertGreaterEqual(summary_data["data"]["total_contacts"], 1)
        self.assertGreaterEqual(summary_data["data"]["total_deals"], 1)
        self.assertGreaterEqual(summary_data["data"]["deals_analyzed"], 1)

        prospect_res = self.client.post(
            "/api/prospect/analyze",
            json={"company_name": "Northwind", "domain": "northwind.com"},
        )
        self.assertEqual(prospect_res.status_code, 200)
        prospect_data = prospect_res.json()
        self.assertEqual(prospect_data["status"], "success")
        self.assertEqual(prospect_data["data"]["company_name"], "Northwind")
        self.assertGreaterEqual(prospect_data["data"]["score"], 0)
        self.assertLessEqual(prospect_data["data"]["score"], 100)


if __name__ == "__main__":
    unittest.main()
