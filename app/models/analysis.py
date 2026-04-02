from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import RiskLevel

if TYPE_CHECKING:
    from app.models.deal import Deal


class ProspectAnalysis(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "prospect_analysis"

    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    industry: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    scraped_excerpt: Mapped[str | None] = mapped_column(Text)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    outreach_message: Mapped[str | None] = mapped_column(Text)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False, default="rule_v1")


class DealAnalysis(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "deal_analysis"

    deal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("deals.id"), nullable=False, index=True)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    inactivity_days: Mapped[int] = mapped_column(Integer, nullable=False)
    interaction_count: Mapped[int] = mapped_column(Integer, nullable=False)
    no_reply: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    churn_risk: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    churn_reason: Mapped[str | None] = mapped_column(String(255))
    model_version: Mapped[str] = mapped_column(String(50), nullable=False, default="rule_v1")

    deal: Mapped["Deal"] = relationship(back_populates="analyses")
