from fastapi import APIRouter, Depends
from app.models.models import User
from app.routers.auth import get_current_user  # adjust import if needed

router = APIRouter(prefix="/users", tags=["User"])


@router.get("/me")
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """
    Returns only the user's number and referral code.
    """
    return {
        "number": current_user.number,
        "referral_code": current_user.referral_code
    }
