from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.dependencies import get_current_user_detached
from app.models import User
from app.services.ai_service import (
    AIServiceError,
    ListingAIAnalysis,
    ReadabilityResult,
    analyze_listing_image,
    check_listing_image_readability,
)

router = APIRouter(prefix="/ai", tags=["ai"])


class AnalyzePhotoRequest(BaseModel):
    object_key: str


class CheckReadabilityRequest(BaseModel):
    object_key: str


def _require_own_object_key(object_key: str, current_user: User) -> None:
    owner_id, _, rest = object_key.partition("/")
    if not rest or owner_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this object key",
        )


@router.post("/analyze-photo", response_model=ListingAIAnalysis)
def analyze_photo(
    payload: AnalyzePhotoRequest,
    current_user: User = Depends(get_current_user_detached),
) -> ListingAIAnalysis:
    _require_own_object_key(payload.object_key, current_user)
    try:
        return analyze_listing_image(payload.object_key)
    except AIServiceError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service temporarily unavailable",
        )


@router.post("/check-readability", response_model=ReadabilityResult)
def check_readability(
    payload: CheckReadabilityRequest,
    current_user: User = Depends(get_current_user_detached),
) -> ReadabilityResult:
    _require_own_object_key(payload.object_key, current_user)
    try:
        return check_listing_image_readability(payload.object_key)
    except AIServiceError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service temporarily unavailable",
        )
