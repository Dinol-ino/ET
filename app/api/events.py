from typing import Any

from fastapi import APIRouter, Body, Depends

from app.api.dependencies import get_event_service
from app.schemas.common import APIResponse
from app.services.event_service import EventService

router = APIRouter(prefix="/api/events", tags=["events"])


@router.post("/process", response_model=APIResponse)
def process_events(
    payload: dict[str, Any] = Body(default_factory=dict),
    service: EventService = Depends(get_event_service),
) -> APIResponse:
    print("Incoming request:", payload)
    limit = _safe_limit(payload.get("limit"))
    events = _normalize_events(payload)
    print("Normalized events:", events)
    result = service.process_events(events=events, limit=limit)
    print("Routing results:", result.get("events", []))
    return APIResponse(status="success", message="Event pipeline processed", data=result)


def _safe_limit(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 100
    return max(1, min(500, parsed))


def _normalize_events(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if "events" in payload:
        events_obj = payload.get("events")
        if isinstance(events_obj, list):
            return [item for item in events_obj if isinstance(item, dict)]
        if isinstance(events_obj, dict):
            return [events_obj]

    if "event" in payload and isinstance(payload.get("event"), dict):
        return [payload["event"]]

    required_keys = {"event_type", "timestamp", "data"}
    if required_keys.issubset(payload.keys()):
        return [
            {
                "event_type": payload.get("event_type"),
                "timestamp": payload.get("timestamp"),
                "data": payload.get("data"),
            }
        ]

    return []
