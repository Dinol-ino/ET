from __future__ import annotations

from pydantic import BaseModel, Field


class EventRequestItem(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=64)
    timestamp: str = Field(..., min_length=1, max_length=128)
    data: dict[str, object] = Field(default_factory=dict)


class EventProcessRequest(BaseModel):
    limit: int = Field(default=100, ge=1, le=500)
    events: list[EventRequestItem] = Field(default_factory=list)
