


# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from app.models.models import UserLevel, Referral

# BONUS_PERCENTAGES = {
#     "A": 0.09,  # 9%
#     "B": 0.03,  # 3%
#     "C": 0.01,  # 1%
# }

# async def process_referral_bonus(db: AsyncSession, purchased_user_id: int):
#     """
#     Calculate and assign referral bonuses when a user buys a PAID level.

#     Referral bonus is based ONLY on earnest_money (cash paid),
#     never on salary.
#     """

#     # 1️⃣ Get purchased user level
#     result = await db.execute(
#         select(UserLevel).where(UserLevel.user_id == purchased_user_id)
#     )
#     purchased_level = result.scalar_one_or_none()

#     # 🚨 Stop if user has no level OR bought free level
#     if not purchased_level or purchased_level.earnest_money <= 0:
#         return 0

#     purchased_amount = purchased_level.earnest_money

#     # 2️⃣ Fetch referrals
#     result = await db.execute(
#         select(Referral).where(Referral.referred_id == purchased_user_id)
#     )
#     referrals = result.scalars().all()

#     total_bonus = 0

#     for referral in referrals:
#         # 3️⃣ Get referrer level
#         result = await db.execute(
#             select(UserLevel).where(UserLevel.user_id == referral.referrer_id)
#         )
#         ref_level = result.scalar_one_or_none()
#         if not ref_level:
#             continue

#         ref_amount = ref_level.earnest_money

#         # 🚨 Skip if referrer is free level
#         if ref_amount <= 0:
#             continue

#         # 4️⃣ Calculate bonus using PAID amounts only
#         bonus_base = min(ref_amount, purchased_amount)
#         percent = BONUS_PERCENTAGES.get(referral.level, 0)

#         bonus = round(bonus_base * percent, 2)
#         if bonus <= 0:
#             continue

#         referral.bonus_amount = bonus
#         referral.is_active = True
#         total_bonus += bonus

#         db.add(referral)

#     await db.commit()
#     return total_bonus




from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
from app.models.models import UserLevel, Referral, Wallet, Transaction, TransactionType

BONUS_PERCENTAGES = {
    "A": 0.09,  # 9%
    "B": 0.03,  # 3%
    "C": 0.01,  # 1%
}

async def process_referral_bonus(db: AsyncSession, purchased_user_id: int):
    """
    Calculate and assign referral bonuses when a user buys a PAID level.
    This now:
      1. Updates the Referral record
      2. Credits the referrer's wallet
      3. Creates a Transaction record
    """

    # 1️⃣ Get purchased user level
    result = await db.execute(
        select(UserLevel).where(UserLevel.user_id == purchased_user_id)
    )
    purchased_level = result.scalar_one_or_none()

    # Stop if user has no level OR bought free level
    if not purchased_level or purchased_level.earnest_money <= 0:
        return 0

    purchased_amount = purchased_level.earnest_money

    # 2️⃣ Fetch referrals
    result = await db.execute(
        select(Referral).where(Referral.referred_id == purchased_user_id)
    )
    referrals = result.scalars().all()

    total_bonus = 0

    for referral in referrals:
        # 3️⃣ Get referrer level
        result = await db.execute(
            select(UserLevel).where(UserLevel.user_id == referral.referrer_id)
        )
        ref_level = result.scalar_one_or_none()
        if not ref_level:
            continue

        # Skip if referrer is free level
        if ref_level.earnest_money <= 0:
            continue

        # 4️⃣ Calculate bonus using PAID amounts only
        bonus_base = min(ref_level.earnest_money, purchased_amount)
        percent = BONUS_PERCENTAGES.get(referral.level, 0)
        bonus = round(bonus_base * percent, 2)
        if bonus <= 0:
            continue

        # 5️⃣ Update Referral
        referral.bonus_amount = bonus
        referral.is_active = True
        db.add(referral)

        # 6️⃣ Credit referrer's wallet
        wallet_result = await db.execute(
            select(Wallet).where(Wallet.user_id == referral.referrer_id)
        )
        wallet = wallet_result.scalar_one_or_none()
        if wallet:
            wallet.income += bonus
            db.add(wallet)

            # 7️⃣ Record Transaction
            transaction = Transaction(
                user_id=referral.referrer_id,
                type=TransactionType.REFERRAL_BONUS.value,
                amount=bonus,
                created_at=datetime.utcnow()
            )
            db.add(transaction)

        total_bonus += bonus

    await db.commit()
    return total_bonus
