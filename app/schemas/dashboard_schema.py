from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_contacts: int
    total_deals: int
    prospects_analyzed: int
    deals_analyzed: int
    high_risk_deals: int
    potential_churn_deals: int
