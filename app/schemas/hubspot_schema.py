from pydantic import BaseModel, Field


class HubSpotSyncRequest(BaseModel):
    limit: int = Field(default=100, ge=1, le=500)
