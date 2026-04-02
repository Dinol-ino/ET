from uuid import UUID

from pydantic import BaseModel


class DealAnalyzeRequest(BaseModel):
    deal_id: UUID
