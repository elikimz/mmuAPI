



# from fastapi import APIRouter, Depends
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from sqlalchemy.orm import selectinload
# from typing import List

# from app.database.database import get_async_db
# from app.models.models import Referral, UserLevel, User
# from app.routers.auth import get_current_user
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
#     - referred user's referral code
#     - referred user's current level (if any)
#     """

#     result = await db.execute(
#         select(Referral)
#         .where(Referral.referrer_id == current_user.id)
#         .options(selectinload(Referral.referred))
#     )

#     referrals = result.scalars().all()
#     response = []

#     for referral in referrals:
#         # Get referred user's level (if exists)
#         level_result = await db.execute(
#             select(UserLevel).where(UserLevel.user_id == referral.referred_id)
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
#                 "referral_code": referral.referred.referral_code,  # ✅ ADDED
#                 "created_at": referral.referred.created_at,
#                 "level": {
#                     "name": user_level.name,
#                     "earnest_money": user_level.earnest_money,
#                     "salary": user_level.salary,
#                     "daily_income": user_level.daily_income,
#                     "monthly_income": user_level.monthly_income,
#                     "annual_income": user_level.annual_income,
#                 } if user_level else None,
#             },
#         })

#     return response






from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from typing import List
from datetime import datetime

from app.database.database import get_async_db
from app.models.models import Referral, User, UserTaskCompleted, UserTask
from app.routers.auth import get_current_user

router = APIRouter(prefix="/referrals", tags=["Referrals"])


@router.get("/me")
async def get_referral_dashboard(
    start_date: str = Query(None),  # format: YYYY-MM-DD
    end_date: str = Query(None),    # format: YYYY-MM-DD
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Returns:
    - Team overview (totals by level, team members, tasks completed)
    - List of all referrals with user and level info
    """

    # 1️⃣ Get all referrals made by current user, eagerly load referred users and their levels
    result = await db.execute(
        select(Referral)
        .where(Referral.referrer_id == current_user.id)
        .options(
            selectinload(Referral.referred).selectinload(User.levels)  # <-- load levels here
        )
    )
    referrals = result.scalars().all()

    # Initialize aggregates
    level_totals = {"A": 0, "B": 0, "C": 0}
    team_members = len(referrals)
    new_members = 0
    tasks_completed_total = 0
    tasks_total = 0  # optional if you want total tasks assigned

    referral_list = []

    # Convert date filters if provided
    start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

    for ref in referrals:
        # Count per level
        level_totals[ref.level] = level_totals.get(ref.level, 0) + 1

        # Count new members based on created_at filter
        if start_dt and end_dt:
            if start_dt <= ref.referred.created_at <= end_dt:
                new_members += 1

        # Count tasks completed for this referred user
        completed_count = await db.scalar(
            select(func.count(UserTaskCompleted.id))
            .where(UserTaskCompleted.user_id == ref.referred_id)
        )
        tasks_completed_total += completed_count or 0

        # Optional: total tasks assigned
        total_tasks_count = await db.scalar(
            select(func.count(UserTask.id))
            .where(UserTask.user_id == ref.referred_id)
        )
        tasks_total += total_tasks_count or 0

        # Prepare individual referral info
        # Get referred user's level safely (already loaded)
        user_level = ref.referred.levels[0] if ref.referred.levels else None

        referral_list.append({
            "id": ref.id,
            "level": ref.level,
            "is_active": ref.is_active,
            "bonus_amount": ref.bonus_amount,
            "created_at": ref.created_at,
            "referred_user": {
                "id": ref.referred.id,
                "number": ref.referred.number,
                "country_code": ref.referred.country_code,
                "referral_code": ref.referred.referral_code,
                "created_at": ref.referred.created_at,
                "level": {
                    "name": user_level.name,
                    "earnest_money": user_level.earnest_money,
                    "salary": user_level.salary,
                    "daily_income": user_level.daily_income,
                    "monthly_income": user_level.monthly_income,
                    "annual_income": user_level.annual_income,
                } if user_level else None,
            }
        })

    # Build team overview response
    team_overview = {
        "A/B/C Total": sum(level_totals.values()),
        "Level A": level_totals.get("A", 0),
        "Level B": level_totals.get("B", 0),
        "Level C": level_totals.get("C", 0),
        "Team Members": team_members,
        "New Members": new_members,
        "A/B/C Tasks Completed": tasks_completed_total,
        "A/B/C Total Tasks": tasks_total
    }

    return {
        "team_overview": team_overview,
        "referrals": referral_list
    }
