from __future__ import annotations

import uuid

from sqlalchemy import desc, distinct, func, select
from sqlalchemy.orm import Session

from app.models.analysis import DealAnalysis, ProspectAnalysis
from app.models.enums import RiskLevel


class AnalysisRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_prospect_analysis(self, payload: dict[str, object]) -> ProspectAnalysis:
        analysis = ProspectAnalysis(
            company_name=str(payload.get("company_name") or "").strip(),
            domain=str(payload.get("domain") or "").strip(),
            industry=self._as_optional_text(payload.get("industry")),
            description=self._as_optional_text(payload.get("description")),
            scraped_excerpt=self._as_optional_text(payload.get("scraped_excerpt")),
            score=int(payload.get("score") or 0),
            reasons=self._as_string_list(payload.get("reasons")),
            outreach_message=self._as_optional_text(payload.get("outreach_message")),
            model_version=str(payload.get("model_version") or "rule_v1"),
        )
        self.db.add(analysis)
        self.db.flush()
        return analysis

    def create_deal_analysis(self, payload: dict[str, object]) -> DealAnalysis:
        deal_id = payload.get("deal_id")
        if not isinstance(deal_id, uuid.UUID):
            deal_id = uuid.UUID(str(deal_id))

        risk_level = payload.get("risk_level")
        if isinstance(risk_level, RiskLevel):
            parsed_risk_level = risk_level
        else:
            parsed_risk_level = RiskLevel[str(risk_level).upper()]

        analysis = DealAnalysis(
            deal_id=deal_id,
            risk_score=int(payload.get("risk_score") or 0),
            risk_level=parsed_risk_level,
            reasons=self._as_string_list(payload.get("reasons")),
            inactivity_days=int(payload.get("inactivity_days") or 0),
            interaction_count=int(payload.get("interaction_count") or 0),
            no_reply=bool(payload.get("no_reply", False)),
            churn_risk=bool(payload.get("churn_risk", False)),
            churn_reason=self._as_optional_text(payload.get("churn_reason")),
            model_version=str(payload.get("model_version") or "rule_v1"),
        )
        self.db.add(analysis)
        self.db.flush()
        return analysis

    def get_latest_deal_analysis(self, deal_id: uuid.UUID) -> DealAnalysis | None:
        stmt = (
            select(DealAnalysis)
            .where(DealAnalysis.deal_id == deal_id)
            .order_by(desc(DealAnalysis.created_at))
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def count_prospect_analyses(self) -> int:
        stmt = select(func.count(ProspectAnalysis.id))
        return int(self.db.execute(stmt).scalar_one())

    def count_deals_analyzed(self) -> int:
        stmt = select(func.count(distinct(DealAnalysis.deal_id)))
        return int(self.db.execute(stmt).scalar_one())

    def count_high_risk_deals(self) -> int:
        stmt = (
            select(func.count(distinct(DealAnalysis.deal_id)))
            .where(DealAnalysis.risk_level == RiskLevel.HIGH)
        )
        return int(self.db.execute(stmt).scalar_one())

    def count_churn_risk_deals(self) -> int:
        stmt = (
            select(func.count(distinct(DealAnalysis.deal_id)))
            .where(DealAnalysis.churn_risk.is_(True))
        )
        return int(self.db.execute(stmt).scalar_one())

    @staticmethod
    def _as_optional_text(value: object) -> str | None:
        text = str(value).strip() if value is not None else ""
        return text or None

    @staticmethod
    def _as_string_list(value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        text = str(value).strip()
        return [text] if text else []
