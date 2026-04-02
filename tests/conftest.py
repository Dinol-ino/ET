from __future__ import annotations

import datetime as dt
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import dependencies
from app.db.base import Base
from app.db import session as db_session
from app.integrations.hubspot_client import HubSpotClient
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.contact_repository import ContactRepository
from app.repositories.deal_repository import DealRepository
from app.services.deal_service import DealService
from app.services.hubspot_service import HubSpotService
from app.services.prospect_service import ProspectService
from app.services.scoring import DealRiskScorer, ProspectScorer, RetentionScorer


class FakeScraperClient:
    def scrape_company_site(self, domain: str) -> str:
        return (
            f"{domain} builds enterprise SaaS for revenue teams with AI-driven automation "
            "and growth analytics capabilities."
        )


class FakeLLMClient:
    def generate_response(self, prompt: str) -> str:
        return "Hello team, sharing a tailored revenue acceleration idea for your pipeline goals."


class FakeHubSpotClient(HubSpotClient):
    def __init__(self) -> None:
        pass

    def fetch_contacts(self, limit: int = 100) -> list[dict[str, object]]:
        return [
            {
                "external_id": "c-1",
                "email": "owner@northwind.com",
                "first_name": "Alex",
                "last_name": "Stone",
                "company_name": "Northwind",
                "domain": "northwind.com",
                "job_title": "Head of Sales",
            }
        ][:limit]

    def fetch_deals(self, limit: int = 100) -> list[dict[str, object]]:
        now = dt.datetime.now(tz=dt.timezone.utc)
        return [
            {
                "external_id": "d-1",
                "name": "Northwind Expansion",
                "amount": "25000",
                "stage": "proposal",
                "pipeline": "default",
                "close_date": (now + dt.timedelta(days=10)).isoformat(),
                "last_activity_at": (now - dt.timedelta(days=11)).isoformat(),
                "contact_external_id": "c-1",
                "activities": [
                    {
                        "activity_type": "EMAIL",
                        "direction": "OUTBOUND",
                        "subject": "Proposal follow-up",
                        "occurred_at": (now - dt.timedelta(days=11)).isoformat(),
                        "replied": False,
                        "details": {"source": "test"},
                    },
                    {
                        "activity_type": "CALL",
                        "direction": "OUTBOUND",
                        "subject": "Budget discussion",
                        "occurred_at": (now - dt.timedelta(days=16)).isoformat(),
                        "replied": False,
                        "details": {"source": "test"},
                    },
                ],
            }
        ][:limit]


@pytest.fixture()
def test_engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def testing_session_local(test_engine):
    return sessionmaker(bind=test_engine, autoflush=False, autocommit=False, expire_on_commit=False)


@pytest.fixture()
def db_session_fixture(testing_session_local) -> Generator[Session, None, None]:
    db = testing_session_local()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(test_engine, testing_session_local) -> Generator[TestClient, None, None]:
    original_engine = db_session.engine
    original_session_local = db_session.SessionLocal

    db_session.engine = test_engine
    db_session.SessionLocal = testing_session_local

    from app.main import app

    def _override_get_prospect_service():
        db = testing_session_local()
        try:
            yield ProspectService(
                analysis_repo=AnalysisRepository(db),
                scraper_client=FakeScraperClient(),
                llm_client=FakeLLMClient(),
                scorer=ProspectScorer(),
            )
        finally:
            db.close()

    def _override_get_deal_service():
        db = testing_session_local()
        try:
            yield DealService(
                deal_repo=DealRepository(db),
                analysis_repo=AnalysisRepository(db),
                contact_repo=ContactRepository(db),
                risk_scorer=DealRiskScorer(),
                retention_scorer=RetentionScorer(),
            )
        finally:
            db.close()

    def _override_get_hubspot_service():
        db = testing_session_local()
        try:
            yield HubSpotService(
                hubspot_client=FakeHubSpotClient(),
                contact_repo=ContactRepository(db),
                deal_repo=DealRepository(db),
            )
        finally:
            db.close()

    app.dependency_overrides[dependencies.get_prospect_service] = _override_get_prospect_service
    app.dependency_overrides[dependencies.get_deal_service] = _override_get_deal_service
    app.dependency_overrides[dependencies.get_hubspot_service] = _override_get_hubspot_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    db_session.engine = original_engine
    db_session.SessionLocal = original_session_local
