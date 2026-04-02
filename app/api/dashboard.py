from fastapi import APIRouter, Depends

from app.api.dependencies import get_deal_service
from app.schemas.common import APIResponse
from app.services.deal_service import DealService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=APIResponse)
def dashboard_summary(service: DealService = Depends(get_deal_service)) -> APIResponse:
    result = service.get_dashboard_summary()
    return APIResponse(status="success", message="Dashboard summary", data=result)
