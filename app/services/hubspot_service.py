from __future__ import annotations

from app.integrations.hubspot_client import HubSpotClient
from app.repositories.contact_repository import ContactRepository
from app.repositories.deal_repository import DealRepository


class HubSpotService:
    def __init__(
        self,
        hubspot_client: HubSpotClient,
        contact_repo: ContactRepository,
        deal_repo: DealRepository,
    ):
        self.hubspot_client = hubspot_client
        self.contact_repo = contact_repo
        self.deal_repo = deal_repo

    def sync_contacts(self, limit: int = 100) -> dict[str, object]:
        contacts = self.hubspot_client.fetch_contacts(limit=limit)
        synced_ids: list[str] = []

        try:
            for payload in contacts:
                if not payload.get("email"):
                    continue
                contact = self.contact_repo.upsert_contact(payload)
                synced_ids.append(str(contact.id))
            self.contact_repo.db.commit()
        except Exception:
            self.contact_repo.db.rollback()
            raise

        return {
            "synced_count": len(synced_ids),
            "contact_ids": synced_ids,
            "source_count": len(contacts),
        }

    def sync_deals(self, limit: int = 100) -> dict[str, object]:
        deals = self.hubspot_client.fetch_deals(limit=limit)
        synced_ids: list[str] = []

        try:
            for payload in deals:
                contact_external_id = str(payload.get("contact_external_id") or "").strip()
                contact = self.contact_repo.get_by_external_id(contact_external_id) if contact_external_id else None

                deal = self.deal_repo.upsert_deal(payload, contact_id=contact.id if contact else None)
                activities = payload.get("activities")
                if isinstance(activities, list):
                    self.deal_repo.replace_activities(deal, activities)
                synced_ids.append(str(deal.id))
            self.deal_repo.db.commit()
        except Exception:
            self.deal_repo.db.rollback()
            raise

        return {
            "synced_count": len(synced_ids),
            "deal_ids": synced_ids,
            "source_count": len(deals),
        }
