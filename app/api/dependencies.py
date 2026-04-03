from fastapi import Depends
from sqlalchemy.orm import Session

from app.events.action_executor import ActionExecutor
from app.events.event_generator import EventGenerator
from app.events.event_router import EventRouter
from app.db.session import get_db
from app.integrations.hubspot_client import HubSpotClient
from app.integrations.llm_client import LLMClient
from app.integrations.scraper import ScraperClient
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.contact_repository import ContactRepository
from app.repositories.deal_repository import DealRepository
from app.services.deal_service import DealService
from app.services.event_service import EventService
from app.services.hubspot_service import HubSpotService
from app.services.prospect_service import ProspectService
from app.services.scoring_engine import HybridScoringEngine
from app.services.scoring import DealRiskScorer, ProspectScorer, RetentionScorer


def get_prospect_service(db: Session = Depends(get_db)) -> ProspectService:
    event_router = EventRouter()
    action_executor = ActionExecutor()
    return ProspectService(
        analysis_repo=AnalysisRepository(db),
        scraper_client=ScraperClient(),
        llm_client=LLMClient(),
        scorer=ProspectScorer(),
        scoring_engine=HybridScoringEngine(),
        event_router=event_router,
        action_executor=action_executor,
    )


def get_deal_service(db: Session = Depends(get_db)) -> DealService:
    event_router = EventRouter()
    action_executor = ActionExecutor()
    return DealService(
        deal_repo=DealRepository(db),
        analysis_repo=AnalysisRepository(db),
        contact_repo=ContactRepository(db),
        risk_scorer=DealRiskScorer(),
        retention_scorer=RetentionScorer(),
        scoring_engine=HybridScoringEngine(),
        event_generator=EventGenerator(),
        event_router=event_router,
        action_executor=action_executor,
    )


def get_hubspot_service(db: Session = Depends(get_db)) -> HubSpotService:
    return HubSpotService(
        hubspot_client=HubSpotClient(),
        contact_repo=ContactRepository(db),
        deal_repo=DealRepository(db),
    )


def get_event_service(db: Session = Depends(get_db)) -> EventService:
    return EventService(
        deal_repo=DealRepository(db),
        event_generator=EventGenerator(),
        event_router=EventRouter(),
        action_executor=ActionExecutor(),
    )
