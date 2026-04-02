from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations.hubspot_client import HubSpotClient
from app.integrations.llm_client import LLMClient
from app.integrations.scraper import ScraperClient
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.contact_repository import ContactRepository
from app.repositories.deal_repository import DealRepository
from app.services.deal_service import DealService
from app.services.hubspot_service import HubSpotService
from app.services.prospect_service import ProspectService
from app.services.scoring import DealRiskScorer, ProspectScorer, RetentionScorer


def get_prospect_service(db: Session = Depends(get_db)) -> ProspectService:
    return ProspectService(
        analysis_repo=AnalysisRepository(db),
        scraper_client=ScraperClient(),
        llm_client=LLMClient(),
        scorer=ProspectScorer(),
    )


def get_deal_service(db: Session = Depends(get_db)) -> DealService:
    return DealService(
        deal_repo=DealRepository(db),
        analysis_repo=AnalysisRepository(db),
        contact_repo=ContactRepository(db),
        risk_scorer=DealRiskScorer(),
        retention_scorer=RetentionScorer(),
    )


def get_hubspot_service(db: Session = Depends(get_db)) -> HubSpotService:
    return HubSpotService(
        hubspot_client=HubSpotClient(),
        contact_repo=ContactRepository(db),
        deal_repo=DealRepository(db),
    )
