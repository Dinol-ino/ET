from pydantic import BaseModel, Field


class ProspectAnalyzeRequest(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=255)
    domain: str = Field(..., min_length=3, max_length=255)
