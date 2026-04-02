from fastapi import APIRouter, Depends

from app.api.dependencies import get_hubspot_service
from app.schemas.common import APIResponse
from app.schemas.hubspot_schema import HubSpotSyncRequest
from app.services.hubspot_service import HubSpotService

router = APIRouter(prefix="/api/hubspot", tags=["hubspot"])


@router.post("/sync-contacts", response_model=APIResponse)
def sync_contacts(
    payload: HubSpotSyncRequest | None = None,
    service: HubSpotService = Depends(get_hubspot_service),
) -> APIResponse:
    limit = payload.limit if payload else 100
    result = service.sync_contacts(limit=limit)
    return APIResponse(status="success", message="Contacts synced", data=result)


@router.post("/sync-deals", response_model=APIResponse)
def sync_deals(
    payload: HubSpotSyncRequest | None = None,
    service: HubSpotService = Depends(get_hubspot_service),
) -> APIResponse:
    limit = payload.limit if payload else 100
    result = service.sync_deals(limit=limit)
    return APIResponse(status="success", message="Deals synced", data=result)
