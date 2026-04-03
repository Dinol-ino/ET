from __future__ import annotations

import datetime as dt

from app.core.utils import utcnow
from app.events.event_schema import EventPayload, make_event
from app.models.deal import Activity, Deal


class EventGenerator:
    """Generates domain events from CRM deal/activity signals."""

    def generate_from_deals(self, deals: list[Deal]) -> list[EventPayload]:
        events: list[EventPayload] = []
        for deal in deals:
            events.extend(self.generate_for_deal(deal))
        return events

    def generate_for_deal(self, deal: Deal) -> list[EventPayload]:
        now = utcnow()
        activities = sorted(deal.activities, key=lambda item: item.occurred_at)
        last_activity_at = self._get_last_activity(deal, activities)
        inactivity_days = max(0, (now - last_activity_at).days)
        interaction_count = len(activities)
        recent_count, prior_count = self._windowed_activity_counts(activities, now)

        data: dict[str, object] = {
            "deal_id": str(deal.id),
            "deal_name": deal.name,
            "contact_id": str(deal.contact_id) if deal.contact_id else None,
            "company_name": (deal.contact.company_name if deal.contact else None),
            "inactivity_days": inactivity_days,
            "interaction_count": interaction_count,
            "recent_count": recent_count,
            "prior_count": prior_count,
            "last_activity_at": last_activity_at.isoformat(),
            "stage": deal.stage,
            "last_interactions": self._last_interactions(activities),
        }

        events: list[EventPayload] = []
        if self._is_new_lead(deal, activities, now):
            events.append(make_event("new_lead", data))
        if inactivity_days > 7:
            events.append(make_event("engagement_drop", data))
        if inactivity_days > 14 and interaction_count < 3:
            events.append(make_event("deal_stagnant", data))
        return events

    @staticmethod
    def _is_new_lead(deal: Deal, activities: list[Activity], now: dt.datetime) -> bool:
        created_at = deal.created_at if deal.created_at.tzinfo else deal.created_at.replace(tzinfo=dt.timezone.utc)
        age_days = max(0, (now - created_at).days)
        return age_days <= 2 and len(activities) <= 1

    @staticmethod
    def _get_last_activity(deal: Deal, activities: list[Activity]) -> dt.datetime:
        baseline = deal.last_activity_at or deal.created_at
        if activities:
            baseline = activities[-1].occurred_at
        if baseline.tzinfo is None:
            baseline = baseline.replace(tzinfo=dt.timezone.utc)
        return baseline

    @staticmethod
    def _windowed_activity_counts(activities: list[Activity], now: dt.datetime) -> tuple[int, int]:
        recent_start = now - dt.timedelta(days=14)
        prior_start = now - dt.timedelta(days=28)

        recent_count = len(
            [activity for activity in activities if EventGenerator._as_aware(activity.occurred_at) >= recent_start]
        )
        prior_count = len(
            [
                activity
                for activity in activities
                if prior_start <= EventGenerator._as_aware(activity.occurred_at) < recent_start
            ]
        )
        return recent_count, prior_count

    @staticmethod
    def _as_aware(value: dt.datetime) -> dt.datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=dt.timezone.utc)
        return value

    @staticmethod
    def _last_interactions(activities: list[Activity], limit: int = 5) -> list[dict[str, object]]:
        tail = sorted(activities, key=lambda item: item.occurred_at, reverse=True)[:limit]
        return [
            {
                "activity_type": activity.activity_type.value,
                "direction": activity.direction.value,
                "occurred_at": activity.occurred_at.isoformat(),
                "replied": activity.replied,
                "subject": activity.subject,
            }
            for activity in tail
        ]
