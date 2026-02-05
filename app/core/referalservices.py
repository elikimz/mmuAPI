

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.models import UserLevel, Referral

BONUS_PERCENTAGES = {
    "A": 0.09,  # 9%
    "B": 0.03,  # 3%
    "C": 0.01,  # 1%
}

async def process_referral_bonus(db: AsyncSession, purchased_user_id: int):
    """
    Calculate and assign referral bonuses when a user buys a level.

    1. Fetch the user who bought a level
    2. Fetch the user's purchased level amount
    3. Find all referrers (A/B/C) for this user
    4. Calculate bonus using lower of referrer and referred level amounts
    5. Mark referral as active ONLY if purchased level price > 0
    """

    # 1. Get the user's purchased level
    result = await db.execute(
        select(UserLevel).where(UserLevel.user_id == purchased_user_id)
    )
    purchased_level = result.scalar_one_or_none()
    if not purchased_level:
        return 0  # User has no purchased level yet

    purchased_amount = purchased_level.salary  # or use earnest_money

    # 2. Get all referrals where this user is referred
    result = await db.execute(
        select(Referral).where(Referral.referred_id == purchased_user_id)
    )
    referrals = result.scalars().all()

    total_bonus = 0  # accumulate total bonus

    for referral in referrals:
        # Get referrer's level
        result = await db.execute(
            select(UserLevel).where(UserLevel.user_id == referral.referrer_id)
        )
        ref_level = result.scalar_one_or_none()
        if not ref_level:
            continue  # skip if referrer has no level

        ref_amount = ref_level.salary  # or earnest_money

        # 3. Calculate bonus (min of referrer and referred levels)
        bonus_base = min(ref_amount, purchased_amount)
        percent = BONUS_PERCENTAGES.get(referral.level, 0)
        referral.bonus_amount = round(bonus_base * percent, 2)
        total_bonus += referral.bonus_amount

        # 4. Mark referral as active ONLY if purchased level price > 0
        referral.is_active = True if purchased_amount > 0 else False

        db.add(referral)

    await db.commit()
    return total_bonus
