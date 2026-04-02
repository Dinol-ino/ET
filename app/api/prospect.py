from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_prospect_service
from app.schemas.common import APIResponse
from app.schemas.prospect_schema import ProspectAnalyzeRequest
from app.services.prospect_service import ProspectService

router = APIRouter(prefix="/api/prospect", tags=["prospect"])


@router.post("/analyze", response_model=APIResponse)
def analyze_prospect(
    payload: ProspectAnalyzeRequest,
    service: ProspectService = Depends(get_prospect_service),
) -> APIResponse:
    try:
        result = service.analyze_prospect(payload.company_name, payload.domain)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return APIResponse(status="success", message="Prospect analysis completed", data=result)
