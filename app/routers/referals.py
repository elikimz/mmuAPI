# from fastapi import APIRouter, Depends
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from sqlalchemy.orm import selectinload
# from typing import List

# from app.database.database import get_async_db
# from app.models.models import Referral, UserLevel
# from app.routers.auth import get_current_user
# from app.models.models import User
# from app.schema.schema import MyReferralResponse

# router = APIRouter(prefix="/referrals", tags=["Referrals"])


# @router.get("/me", response_model=List[MyReferralResponse])
# async def get_my_referrals(
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_async_db),
# ):
#     """
#     Get all users I referred, including:
#     - referral info
#     - referred user details
#     - referred user's current level (if any)
#     """

#     result = await db.execute(
#         select(Referral)
#         .where(Referral.referrer_id == current_user.id)
#         .options(
#             selectinload(Referral.referred)
#         )
#     )

#     referrals = result.scalars().all()
#     response = []

#     for referral in referrals:
#         # Get referred user's level (if exists)
#         level_result = await db.execute(
#             select(UserLevel)
#             .where(UserLevel.user_id == referral.referred_id)
#         )
#         user_level = level_result.scalar_one_or_none()

#         response.append({
#             "id": referral.id,
#             "level": referral.level,
#             "is_active": referral.is_active,
#             "bonus_amount": referral.bonus_amount,
#             "created_at": referral.created_at,
#             "referred_user": {
#                 "id": referral.referred.id,
#                 "number": referral.referred.number,
#                 "country_code": referral.referred.country_code,
#                 "created_at": referral.referred.created_at,
#                 "level": {
#                     "name": user_level.name,
#                     "earnest_money": user_level.earnest_money,
#                     "salary": user_level.salary,
#                     "daily_income": user_level.daily_income,
#                     "monthly_income": user_level.monthly_income,
#                     "annual_income": user_level.annual_income,
#                 } if user_level else None
#             }
#         })

#     return response





from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List

from app.database.database import get_async_db
from app.models.models import Referral, UserLevel, User
from app.routers.auth import get_current_user
from app.schema.schema import MyReferralResponse

router = APIRouter(prefix="/referrals", tags=["Referrals"])


@router.get("/me", response_model=List[MyReferralResponse])
async def get_my_referrals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get all users I referred, including:
    - referral info
    - referred user details
    - referred user's referral code
    - referred user's current level (if any)
    """

    result = await db.execute(
        select(Referral)
        .where(Referral.referrer_id == current_user.id)
        .options(selectinload(Referral.referred))
    )

    referrals = result.scalars().all()
    response = []

    for referral in referrals:
        # Get referred user's level (if exists)
        level_result = await db.execute(
            select(UserLevel).where(UserLevel.user_id == referral.referred_id)
        )
        user_level = level_result.scalar_one_or_none()

        response.append({
            "id": referral.id,
            "level": referral.level,
            "is_active": referral.is_active,
            "bonus_amount": referral.bonus_amount,
            "created_at": referral.created_at,
            "referred_user": {
                "id": referral.referred.id,
                "number": referral.referred.number,
                "country_code": referral.referred.country_code,
                "referral_code": referral.referred.referral_code,  # ✅ ADDED
                "created_at": referral.referred.created_at,
                "level": {
                    "name": user_level.name,
                    "earnest_money": user_level.earnest_money,
                    "salary": user_level.salary,
                    "daily_income": user_level.daily_income,
                    "monthly_income": user_level.monthly_income,
                    "annual_income": user_level.annual_income,
                } if user_level else None,
            },
        })

    return response
