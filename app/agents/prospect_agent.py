from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.deterministic_engine import DeterministicDecisionEngine
from app.integrations.llm_client import LLMClient


def fetch_data(state: dict[str, Any]) -> dict[str, Any]:
    company = str(state.get("company_name") or "company").strip()
    domain = str(state.get("domain") or "").strip()
    state["data"] = f"Company: {company}. Domain: {domain or 'unknown'}."
    return state


def analyze(state: dict[str, Any], llm_client: LLMClient) -> dict[str, Any]:
    prompt = (
        "Analyze this company profile and return concise sales notes.\n\n"
        f"INPUT: {state.get('data', '')}\n"
        "OUTPUT: industry, one-line summary, and qualification score signals."
    )
    state["analysis"] = llm_client.generate_response(prompt)
    return state


def generate_email(state: dict[str, Any], llm_client: LLMClient) -> dict[str, Any]:
    prompt = (
        "Write a concise personalized cold email from this analysis.\n\n"
        f"ANALYSIS: {state.get('analysis', '')}\n"
    )
    state["email"] = llm_client.generate_response(prompt)
    return state


def build_graph(llm_client: LLMClient):
    builder = StateGraph(dict)
    builder.add_node("fetch", fetch_data)
    builder.add_node("analyze", lambda state: analyze(state, llm_client))
    builder.add_node("email", lambda state: generate_email(state, llm_client))
    builder.set_entry_point("fetch")
    builder.add_edge("fetch", "analyze")
    builder.add_edge("analyze", "email")
    builder.add_edge("email", END)
    return builder.compile()


class ProspectAgent:
    """Prospect agent that combines deterministic event decisions with an outreach workflow."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()
        self.engine = DeterministicDecisionEngine()
        self._graph = None

    def handle_event(
        self,
        event_data: dict[str, Any],
        crm_data: dict[str, Any],
        engagement_metrics: dict[str, Any],
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        decision = self.engine.decide(
            agent_name="prospect_agent",
            event_data=event_data,
            crm_data=crm_data,
            engagement_metrics=engagement_metrics,
            history=history,
        )

        company_name = str(crm_data.get("company_name") or "").strip()
        domain = str(crm_data.get("domain") or "").strip()
        outreach = self.generate_outreach_email(company_name=company_name, domain=domain)
        if outreach:
            action = decision.get("recommended_action")
            if isinstance(action, dict):
                action["type"] = "email"
                action["message"] = outreach
                decision["recommended_action"] = action

        return decision

    def generate_outreach_email(self, *, company_name: str, domain: str) -> str:
        if not company_name:
            return ""
        if self._graph is None:
            self._graph = build_graph(self.llm_client)
        try:
            result = self._graph.invoke({"company_name": company_name, "domain": domain})
        except Exception:
            return ""

        if isinstance(result, dict):
            email = str(result.get("email") or "").strip()
            return email
        return ""
