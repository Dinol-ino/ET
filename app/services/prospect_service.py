from __future__ import annotations

import json
import re

from app.core.utils import now_iso
from app.events.action_executor import ActionExecutor
from app.events.event_router import EventRouter
from app.events.event_schema import make_event
from app.integrations.llm_client import LLMClient
from app.integrations.scraper import ScraperClient
from app.repositories.analysis_repository import AnalysisRepository
from app.services.scoring_engine import HybridScoringEngine
from app.services.scoring import ProspectScorer


class ProspectService:
    def __init__(
        self,
        analysis_repo: AnalysisRepository,
        scraper_client: ScraperClient,
        llm_client: LLMClient,
        scorer: ProspectScorer,
        scoring_engine: HybridScoringEngine | None = None,
        event_router: EventRouter | None = None,
        action_executor: ActionExecutor | None = None,
    ):
        self.analysis_repo = analysis_repo
        self.scraper_client = scraper_client
        self.llm_client = llm_client
        self.scorer = scorer
        self.scoring_engine = scoring_engine or HybridScoringEngine()
        self.event_router = event_router
        self.action_executor = action_executor

    def analyze_prospect(self, company_name: str, domain: str) -> dict[str, object]:
        scraped_text = self.scraper_client.scrape_company_site(domain)
        industry = self._infer_industry(scraped_text, domain)
        description = self._summarize_description(company_name, scraped_text)
        score_result = self.scorer.score(company_name, domain, industry, scraped_text)

        crm_data = {
            "company_name": company_name,
            "domain": domain,
            "industry": industry,
            "internal_score": score_result.score,
        }
        external_data = {
            "description": description,
            "scraped_excerpt": scraped_text[:1000],
        }
        engagement_metrics = {
            "recent_interactions": None,
            "reply_rate": None,
            "last_activity_at": None,
        }

        decision_prompt = self._build_sales_decision_prompt(crm_data, external_data, engagement_metrics)
        llm_raw = self.llm_client.generate_response(decision_prompt)
        llm_payload = self._parse_json_payload(llm_raw)

        llm_score = self._safe_score(llm_payload.get("score"), fallback=score_result.score)
        risk_flags = self._safe_string_list(llm_payload.get("risk_flags"))
        insights = self._safe_text(llm_payload.get("insights"))
        recommended_action = self._safe_text(llm_payload.get("recommended_action"))
        confidence = self._safe_confidence(llm_payload.get("confidence"))

        hybrid = self.scoring_engine.calculate(
            crm_data={
                "company_name": company_name,
                "industry": industry,
                "industry_fit": industry,
                "company_size": self._infer_company_size(scraped_text),
            },
            engagement_metrics={
                "email_replies": 0,
                "meetings_scheduled": 0,
                "days_since_last_interaction": 30,
            },
            llm_output={"score": llm_score},
        )
        final_score = int(hybrid["final_score"])

        reasons = list(score_result.reasons)
        if insights:
            reasons.append(f"LLM insight: {insights}")
        reasons.extend(risk_flags)
        reasons.append(f"Confidence: {confidence}")
        reasons.append(str(hybrid["reasoning"]))
        if not recommended_action:
            recommended_action = (
                "Send a concise outreach note focused on revenue process pain points and ask for a 15-minute discovery call."
            )

        event_result: dict[str, object] | None = None
        if self.event_router is not None:
            lead_event = make_event(
                "new_lead",
                {
                    "company_name": company_name,
                    "domain": domain,
                    "industry": industry,
                    "source": "prospect_analysis",
                },
                timestamp=now_iso(),
            )
            event_decision = self.event_router.route_event(
                event=lead_event,
                crm_data={
                    "company_name": company_name,
                    "domain": domain,
                    "industry": industry,
                    "score": final_score,
                },
                engagement_metrics=engagement_metrics,
                history=[],
            )
            execution_result = (
                self.action_executor.execute(event_decision, event=lead_event.to_dict())
                if self.action_executor is not None
                else {"status": "skipped"}
            )
            event_result = {
                "event": lead_event.to_dict(),
                "decision": event_decision,
                "execution": execution_result,
            }
            action_message = str(event_decision.get("recommended_action", {}).get("message") or "").strip()
            if action_message:
                recommended_action = action_message

        try:
            analysis = self.analysis_repo.create_prospect_analysis(
                {
                    "company_name": company_name,
                    "domain": domain,
                    "industry": industry,
                    "description": description,
                    "scraped_excerpt": scraped_text[:500],
                    "score": final_score,
                    "reasons": reasons,
                    "outreach_message": recommended_action,
                    "model_version": "prospect_llm_v2",
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
            "event_result": event_result,
            "score_components": hybrid["components"],
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
    def _build_sales_decision_prompt(
        crm_data: dict[str, object],
        external_data: dict[str, object],
        engagement_metrics: dict[str, object],
    ) -> str:
        crm_json = json.dumps(crm_data, ensure_ascii=True)
        external_json = json.dumps(external_data, ensure_ascii=True)
        engagement_json = json.dumps(engagement_metrics, ensure_ascii=True)

        return (
            "You are designing a production-grade AI agent for a sales intelligence system.\n\n"
            "Your goal is NOT to generate generic responses, but to:\n"
            "1. Analyze structured CRM and external data\n"
            "2. Identify key signals and patterns\n"
            "3. Make a clear, explainable decision\n"
            "4. Recommend specific, actionable steps\n\n"
            "INPUT:\n"
            f"- CRM Data: {crm_json}\n"
            f"- External Data: {external_json}\n"
            f"- Engagement Signals: {engagement_json}\n\n"
            "TASK:\n"
            "1. Extract key insights (industry, size, engagement level)\n"
            "2. Identify risks or opportunities\n"
            "3. Assign a score (0-100) with reasoning\n"
            "4. Generate a recommended action:\n"
            "   - outreach message OR\n"
            "   - recovery strategy OR\n"
            "   - retention action\n"
            "5. Provide confidence level (low/medium/high)\n\n"
            "RULES:\n"
            "- Do NOT hallucinate missing data\n"
            "- Be concise but specific\n"
            "- Every decision must include reasoning\n"
            "- Prefer actionable outputs over descriptions\n\n"
            "OUTPUT FORMAT (STRICT JSON):\n"
            "{\n"
            '  "insights": "...",\n'
            '  "score": 0,\n'
            '  "risk_flags": [],\n'
            '  "recommended_action": "...",\n'
            '  "confidence": "high"\n'
            "}\n"
        )

    @staticmethod
    def _parse_json_payload(response: str) -> dict[str, object]:
        raw = (response or "").strip()
        if not raw:
            return {}

        # Some local models wrap JSON in markdown fences; extract the first object-shaped block.
        fenced_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", raw, flags=re.IGNORECASE)
        candidate = fenced_match.group(1) if fenced_match else raw

        try:
            parsed = json.loads(candidate)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            pass

        loose_match = re.search(r"\{[\s\S]*\}", raw)
        if not loose_match:
            return {}

        try:
            parsed = json.loads(loose_match.group(0))
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _safe_score(value: object, fallback: int) -> int:
        try:
            score = int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return fallback
        return max(0, min(100, score))

    @staticmethod
    def _safe_text(value: object) -> str:
        text = str(value).strip() if value is not None else ""
        return text

    @staticmethod
    def _safe_string_list(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    @staticmethod
    def _safe_confidence(value: object) -> str:
        normalized = str(value).strip().lower()
        if normalized in {"low", "medium", "high"}:
            return normalized
        return "medium"

    @staticmethod
    def _infer_company_size(scraped_text: str) -> int:
        text = scraped_text.lower()
        if "enterprise" in text:
            return 500
        if "mid-market" in text or "mid market" in text:
            return 200
        if "startup" in text:
            return 25
        return 100
