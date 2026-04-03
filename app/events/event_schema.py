from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.core.utils import now_iso

EventType = Literal["new_lead", "engagement_drop", "deal_stagnant"]
Priority = Literal["high", "medium", "low"]
ActionType = Literal["email", "call", "escalate"]
ActionTiming = Literal["immediate", "24h", "3 days"]


@dataclass(slots=True)
class EventPayload:
    event_type: EventType
    timestamp: str
    data: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "data": self.data,
        }


def make_event(event_type: EventType, data: dict[str, object], timestamp: str | None = None) -> EventPayload:
    return EventPayload(event_type=event_type, timestamp=timestamp or now_iso(), data=data)


SalesEvent = EventPayload
