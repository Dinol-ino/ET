from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.utils import parse_datetime
from app.models.deal import Activity, Deal
from app.models.enums import ActivityDirection, ActivityType


class DealRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, deal_id: uuid.UUID) -> Deal | None:
        stmt = (
            select(Deal)
            .where(Deal.id == deal_id)
            .options(selectinload(Deal.activities), selectinload(Deal.analyses), selectinload(Deal.contact))
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_external_id(self, external_id: str) -> Deal | None:
        stmt = select(Deal).where(Deal.external_id == external_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def upsert_deal(self, payload: dict[str, object], contact_id: uuid.UUID | None = None) -> Deal:
        external_id = self._as_optional_text(payload.get("external_id"))
        name = self._as_optional_text(payload.get("name"))
        if not name:
            raise ValueError("Deal name is required")

        deal = self.get_by_external_id(external_id) if external_id else None
        if deal is None:
            deal = Deal(name=name)
            self.db.add(deal)

        deal.external_id = external_id
        deal.contact_id = contact_id
        deal.name = name
        deal.amount = self._as_decimal(payload.get("amount"))
        deal.stage = self._as_optional_text(payload.get("stage"))
        deal.pipeline = self._as_optional_text(payload.get("pipeline"))
        deal.close_date = parse_datetime(payload.get("close_date"))
        deal.last_activity_at = parse_datetime(payload.get("last_activity_at"))

        self.db.flush()
        return deal

    def replace_activities(self, deal: Deal, activities_payload: list[dict[str, object]]) -> None:
        deal.activities = [self._build_activity(deal.id, payload) for payload in activities_payload]
        if deal.activities:
            deal.last_activity_at = max(activity.occurred_at for activity in deal.activities)

    def list_deals(self, limit: int = 100, offset: int = 0) -> list[Deal]:
        stmt = (
            select(Deal)
            .order_by(Deal.created_at.desc())
            .offset(offset)
            .limit(limit)
            .options(selectinload(Deal.activities), selectinload(Deal.analyses), selectinload(Deal.contact))
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_all_deals(self) -> list[Deal]:
        stmt = select(Deal).options(selectinload(Deal.activities), selectinload(Deal.analyses), selectinload(Deal.contact))
        return list(self.db.execute(stmt).scalars().all())

    def count(self) -> int:
        stmt = select(func.count(Deal.id))
        return int(self.db.execute(stmt).scalar_one())

    def _build_activity(self, deal_id: uuid.UUID, payload: dict[str, object]) -> Activity:
        activity_type = self._parse_activity_type(payload.get("activity_type"))
        direction = self._parse_direction(payload.get("direction"))
        occurred_at = parse_datetime(payload.get("occurred_at"))
        if occurred_at is None:
            raise ValueError("Activity occurred_at is required")

        replied = bool(payload.get("replied", False))
        details = payload.get("details")
        if details is not None and not isinstance(details, dict):
            details = {"raw": str(details)}

        return Activity(
            deal_id=deal_id,
            activity_type=activity_type,
            direction=direction,
            subject=self._as_optional_text(payload.get("subject")),
            occurred_at=occurred_at,
            replied=replied,
            details=details,
        )

    @staticmethod
    def _parse_activity_type(value: object) -> ActivityType:
        text = str(value or "").upper().strip()
        if text in ActivityType.__members__:
            return ActivityType[text]
        for member in ActivityType:
            if member.value == text:
                return member
        return ActivityType.EMAIL

    @staticmethod
    def _parse_direction(value: object) -> ActivityDirection:
        text = str(value or "").upper().strip()
        if text in ActivityDirection.__members__:
            return ActivityDirection[text]
        for member in ActivityDirection:
            if member.value == text:
                return member
        return ActivityDirection.OUTBOUND

    @staticmethod
    def _as_decimal(value: object) -> Decimal | None:
        if value in (None, ""):
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None

    @staticmethod
    def _as_optional_text(value: object) -> str | None:
        text = str(value).strip() if value is not None else ""
        return text or None
