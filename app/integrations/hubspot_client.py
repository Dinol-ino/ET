from __future__ import annotations

import datetime as dt
from typing import Any

import requests

from app.core.config import settings


class HubSpotClient:
    def __init__(self) -> None:
        self.base_url = settings.hubspot_base_url.rstrip("/")
        self.api_key = settings.hubspot_api_key.strip()
        self.timeout = settings.request_timeout_seconds

    def fetch_contacts(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self.api_key:
            return self._mock_contacts()

        payload = self._get(
            "/crm/v3/objects/contacts",
            params={
                "limit": limit,
                "properties": "email,firstname,lastname,company,website,jobtitle",
            },
        )
        results = payload.get("results", []) if isinstance(payload, dict) else []
        return [self._normalize_contact(item) for item in results]

    def fetch_deals(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self.api_key:
            return self._mock_deals()

        payload = self._get(
            "/crm/v3/objects/deals",
            params={
                "limit": limit,
                "properties": "dealname,amount,dealstage,pipeline,closedate,hs_lastmodifieddate,associatedcontactid",
            },
        )
        results = payload.get("results", []) if isinstance(payload, dict) else []
        return [self._normalize_deal(item) for item in results]

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return {}

    @staticmethod
    def _normalize_contact(item: dict[str, Any]) -> dict[str, Any]:
        properties = item.get("properties", {}) if isinstance(item, dict) else {}
        return {
            "external_id": str(item.get("id") or "").strip() or None,
            "email": str(properties.get("email") or "").strip(),
            "first_name": properties.get("firstname"),
            "last_name": properties.get("lastname"),
            "company_name": properties.get("company"),
            "domain": properties.get("website"),
            "job_title": properties.get("jobtitle"),
        }

    @staticmethod
    def _normalize_deal(item: dict[str, Any]) -> dict[str, Any]:
        properties = item.get("properties", {}) if isinstance(item, dict) else {}
        return {
            "external_id": str(item.get("id") or "").strip() or None,
            "name": str(properties.get("dealname") or "Unnamed Deal").strip(),
            "amount": properties.get("amount"),
            "stage": properties.get("dealstage"),
            "pipeline": properties.get("pipeline"),
            "close_date": properties.get("closedate"),
            "last_activity_at": properties.get("hs_lastmodifieddate"),
            "contact_external_id": properties.get("associatedcontactid"),
            "activities": [],
        }

    @staticmethod
    def _mock_contacts() -> list[dict[str, Any]]:
        return [
            {
                "external_id": "demo-contact-1",
                "email": "jane@acme.com",
                "first_name": "Jane",
                "last_name": "Miller",
                "company_name": "Acme Corp",
                "domain": "acme.com",
                "job_title": "VP Sales",
            },
            {
                "external_id": "demo-contact-2",
                "email": "sam@globex.com",
                "first_name": "Sam",
                "last_name": "Reed",
                "company_name": "Globex",
                "domain": "globex.com",
                "job_title": "Director Revenue Ops",
            },
        ]

    @classmethod
    def _mock_deals(cls) -> list[dict[str, Any]]:
        now = dt.datetime.now(tz=dt.timezone.utc)
        return [
            {
                "external_id": "demo-deal-1",
                "name": "Acme Expansion",
                "amount": "45000",
                "stage": "proposal",
                "pipeline": "default",
                "close_date": (now + dt.timedelta(days=21)).isoformat(),
                "last_activity_at": (now - dt.timedelta(days=10)).isoformat(),
                "contact_external_id": "demo-contact-1",
                "activities": [
                    {
                        "activity_type": "EMAIL",
                        "direction": "OUTBOUND",
                        "subject": "Pricing follow-up",
                        "occurred_at": (now - dt.timedelta(days=10)).isoformat(),
                        "replied": False,
                        "details": {"source": "mock"},
                    },
                    {
                        "activity_type": "CALL",
                        "direction": "OUTBOUND",
                        "subject": "Discovery call",
                        "occurred_at": (now - dt.timedelta(days=15)).isoformat(),
                        "replied": False,
                        "details": {"source": "mock"},
                    },
                ],
            },
            {
                "external_id": "demo-deal-2",
                "name": "Globex Renewal",
                "amount": "12000",
                "stage": "negotiation",
                "pipeline": "renewal",
                "close_date": (now + dt.timedelta(days=14)).isoformat(),
                "last_activity_at": (now - dt.timedelta(days=2)).isoformat(),
                "contact_external_id": "demo-contact-2",
                "activities": [
                    {
                        "activity_type": "EMAIL",
                        "direction": "OUTBOUND",
                        "subject": "Renewal options",
                        "occurred_at": (now - dt.timedelta(days=6)).isoformat(),
                        "replied": False,
                        "details": {"source": "mock"},
                    },
                    {
                        "activity_type": "EMAIL",
                        "direction": "INBOUND",
                        "subject": "Re: Renewal options",
                        "occurred_at": (now - dt.timedelta(days=2)).isoformat(),
                        "replied": True,
                        "details": {"source": "mock"},
                    },
                    {
                        "activity_type": "MEETING",
                        "direction": "OUTBOUND",
                        "subject": "Commercial review",
                        "occurred_at": (now - dt.timedelta(days=1)).isoformat(),
                        "replied": True,
                        "details": {"source": "mock"},
                    },
                ],
            },
        ]
