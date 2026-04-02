from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_deal_service
from app.schemas.common import APIResponse
from app.schemas.deal_schema import DealAnalyzeRequest
from app.services.deal_service import DealService

router = APIRouter(prefix="/api/deal", tags=["deal"])


@router.post("/analyze", response_model=APIResponse)
def analyze_deal(
    payload: DealAnalyzeRequest,
    service: DealService = Depends(get_deal_service),
) -> APIResponse:
    try:
        result = service.analyze_deal(payload.deal_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return APIResponse(status="success", message="Deal analysis completed", data=result)


@router.post("/analyze-all", response_model=APIResponse)
def analyze_all_deals(service: DealService = Depends(get_deal_service)) -> APIResponse:
    result = service.analyze_all_deals()
    return APIResponse(status="success", message="Bulk deal analysis completed", data=result)
