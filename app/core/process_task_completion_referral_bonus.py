



# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from datetime import datetime

# from app.models.models import (
#     User,
#     UserTask,
#     Referral,
#     Wallet,
#     Transaction,
#     TransactionType,
# )

# REBATE_AMOUNT = 1.0  # 1 bob


# async def process_task_completion_referral_bonus(
#     db: AsyncSession,
#     completed_user_id: int,
# ):
#     """
#     Give KES 1 to A-level referrer when a referred user
#     completes ALL their tasks and both users are active.
#     """

#     # 1. Check if user still has incomplete tasks and is active
#     result = await db.execute(
#         select(UserTask)
#         .join(User, UserTask.user_id == User.id)
#         .where(
#             UserTask.user_id == completed_user_id,
#             UserTask.completed == False,
#             User.is_active == True  # ensure referred user is active
#         )
#     )
#     incomplete_task = result.scalar_one_or_none()
#     if incomplete_task:
#         return 0  # Not all tasks completed yet or user inactive

#     # 2. Get A-level referral where bonus not yet paid and referrer is active
#     result = await db.execute(
#         select(Referral)
#         .join(User, Referral.referrer_id == User.id)
#         .where(
#             Referral.referred_id == completed_user_id,
#             Referral.level == "A",
#             Referral.is_active == False,  # bonus not yet paid
#             User.is_active == True  # ensure referrer is active
#         )
#     )
#     referral = result.scalar_one_or_none()
#     if not referral:
#         return 0  # No eligible A referrer

#     # 3. Credit referrer's wallet
#     result = await db.execute(
#         select(Wallet).where(Wallet.user_id == referral.referrer_id)
#     )
#     wallet = result.scalar_one_or_none()
#     if not wallet:
#         return 0

#     wallet.income += REBATE_AMOUNT

#     # 4. Record transaction
#     db.add(
#         Transaction(
#             user_id=referral.referrer_id,
#             type=TransactionType.REFERRAL_REBATE.value,
#             amount=REBATE_AMOUNT,
#             created_at=datetime.utcnow()
#         )
#     )

#     # 5. Mark referral as paid/active
#     referral.is_active = True

#     db.add(wallet)
#     db.add(referral)

#     await db.commit()
#     return REBATE_AMOUNT





from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime

from app.models.models import (
    User,
    UserTask,
    Referral,
    Wallet,
    Transaction,
    TransactionType,
)

REBATE_AMOUNT = 1.0  # 1 bob

async def process_task_completion_referral_bonus(
    db: AsyncSession,
    completed_user_id: int,
):
    """
    Give KES 1 to A-level referrer when a referred user
    completes ALL their tasks and both users are active.
    """
    try:
        # 1. Check if user still has incomplete tasks and is active
        result = await db.execute(
            select(UserTask)
            .join(User, UserTask.user_id == User.id)
            .where(
                UserTask.user_id == completed_user_id,
                UserTask.completed == False,
                User.is_active == True  # Ensure referred user is active
            )
        )
        incomplete_task = result.scalar_one_or_none()
        if incomplete_task:
            print("User has incomplete tasks. No rebate awarded.")
            return 0

        # 2. Get A-level referral where bonus not yet paid and referrer is active
        result = await db.execute(
            select(Referral)
            .join(User, Referral.referrer_id == User.id)
            .where(
                Referral.referred_id == completed_user_id,
                Referral.level == "A",
                Referral.is_active == False,  # Bonus not yet paid
                User.is_active == True  # Ensure referrer is active
            )
        )
        referral = result.scalar_one_or_none()
        if not referral:
            print("No eligible A-level referral found.")
            return 0

        # 3. Credit referrer's wallet
        result = await db.execute(
            select(Wallet).where(Wallet.user_id == referral.referrer_id)
        )
        wallet = result.scalar_one_or_none()
        if not wallet:
            print("Referrer wallet not found.")
            return 0

        wallet.income += REBATE_AMOUNT

        # 4. Record transaction
        transaction = Transaction(
            user_id=referral.referrer_id,
            type=TransactionType.REFERRAL_REBATE,
            amount=REBATE_AMOUNT,
            created_at=datetime.utcnow()
        )
        db.add(transaction)

        # 5. Mark referral as paid/active
        referral.is_active = True
        db.add(referral)

        await db.commit()
        print(f"Rebate of {REBATE_AMOUNT} credited to referrer {referral.referrer_id}.")
        return REBATE_AMOUNT

    except Exception as e:
        await db.rollback()
        print(f"Error in referral rebate process: {e}")
        return 0
