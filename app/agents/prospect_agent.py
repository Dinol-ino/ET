from __future__ import annotations


class ProspectAgent:
    """Placeholder agent interface for future LangGraph-powered prospect workflows."""

    def enrich_recommendation(self, company_name: str, score: int) -> str:
        if score >= 70:
            return f"{company_name}: prioritize high-touch outreach sequence."
        if score >= 40:
            return f"{company_name}: run a nurture sequence before direct pitch."
        return f"{company_name}: gather more intent signals before outreach."
