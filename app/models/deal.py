from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ActivityDirection, ActivityType

if TYPE_CHECKING:
    from app.models.analysis import DealAnalysis
    from app.models.contact import Contact


class Deal(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "deals"

    external_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("contacts.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    stage: Mapped[str | None] = mapped_column(String(120), index=True)
    pipeline: Mapped[str | None] = mapped_column(String(120))
    close_date: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    last_activity_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    contact: Mapped["Contact | None"] = relationship(back_populates="deals")
    activities: Mapped[list["Activity"]] = relationship(
        back_populates="deal", cascade="all, delete-orphan", order_by="Activity.occurred_at"
    )
    analyses: Mapped[list["DealAnalysis"]] = relationship(
        back_populates="deal", cascade="all, delete-orphan", order_by="DealAnalysis.created_at"
    )


class Activity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "activities"

    deal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("deals.id"), index=True, nullable=False)
    activity_type: Mapped[ActivityType] = mapped_column(Enum(ActivityType), nullable=False)
    direction: Mapped[ActivityDirection] = mapped_column(
        Enum(ActivityDirection), nullable=False, default=ActivityDirection.OUTBOUND
    )
    subject: Mapped[str | None] = mapped_column(String(255))
    occurred_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    replied: Mapped[bool] = mapped_column(default=False, nullable=False)
    details: Mapped[dict[str, object] | None] = mapped_column(JSON)

    deal: Mapped[Deal] = relationship(back_populates="activities")
