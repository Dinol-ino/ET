from __future__ import annotations

from app.integrations.llm_client import LLMClient
from app.integrations.scraper import ScraperClient
from app.repositories.analysis_repository import AnalysisRepository
from app.services.scoring import ProspectScorer


class ProspectService:
    def __init__(
        self,
        analysis_repo: AnalysisRepository,
        scraper_client: ScraperClient,
        llm_client: LLMClient,
        scorer: ProspectScorer,
    ):
        self.analysis_repo = analysis_repo
        self.scraper_client = scraper_client
        self.llm_client = llm_client
        self.scorer = scorer

    def analyze_prospect(self, company_name: str, domain: str) -> dict[str, object]:
        scraped_text = self.scraper_client.scrape_company_site(domain)
        industry = self._infer_industry(scraped_text, domain)
        description = self._summarize_description(company_name, scraped_text)
        score_result = self.scorer.score(company_name, domain, industry, scraped_text)

        outreach_prompt = self._build_outreach_prompt(company_name, industry, description, score_result.score)
        outreach_message = self.llm_client.generate_response(outreach_prompt)

        try:
            analysis = self.analysis_repo.create_prospect_analysis(
                {
                    "company_name": company_name,
                    "domain": domain,
                    "industry": industry,
                    "description": description,
                    "scraped_excerpt": scraped_text[:500],
                    "score": score_result.score,
                    "reasons": score_result.reasons,
                    "outreach_message": outreach_message,
                    "model_version": "prospect_rule_v1",
                }
            )
            self.analysis_repo.db.commit()
        except Exception:
            self.analysis_repo.db.rollback()
            raise

        return {
            "analysis_id": str(analysis.id),
            "company_name": analysis.company_name,
            "domain": analysis.domain,
            "industry": analysis.industry,
            "description": analysis.description,
            "score": analysis.score,
            "reasons": analysis.reasons,
            "outreach_message": analysis.outreach_message,
            "created_at": analysis.created_at.isoformat(),
        }

    def _infer_industry(self, scraped_text: str, domain: str) -> str:
        text = f"{scraped_text} {domain}".lower()
        signals = {
            "SaaS": ["saas", "software", "platform", "api"],
            "FinTech": ["payments", "lending", "finance", "banking"],
            "HealthTech": ["health", "clinical", "patient", "medical"],
            "E-commerce": ["store", "shopping", "checkout", "cart"],
            "Consulting": ["consulting", "advisory", "transformation", "strategy"],
        }

        for industry, keywords in signals.items():
            if any(keyword in text for keyword in keywords):
                return industry
        return "General B2B"

    @staticmethod
    def _summarize_description(company_name: str, scraped_text: str) -> str:
        snippet = " ".join(scraped_text.split()[:55])
        if not snippet:
            return f"{company_name} operates in a B2B segment with limited public detail available."
        return f"{company_name} profile: {snippet}"

    @staticmethod
    def _build_outreach_prompt(company_name: str, industry: str, description: str, score: int) -> str:
        return (
            "Create a concise outbound sales email. "
            f"Company: {company_name}. Industry: {industry}. Score: {score}/100. "
            f"Profile: {description}."
        )
