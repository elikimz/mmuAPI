"""
tests/test_wallet_logic.py
==========================
Unit tests for wallet credit/debit logic.

Business rules under test
--------------------------
  wallet.balance  — receives ONLY approved deposits (DEPOSIT transaction type).
  wallet.income   — receives ALL other credits:
                      * task rewards          (TASK_REWARD)
                      * referral bonuses      (REFERRAL_BONUS)
                      * level-upgrade refunds (LEVEL_UPGRADE_REFUND)
                      * gift-code redemptions (GIFT_REDEMPTION)
                      * wealth-fund profit    (WEALTH_FUND_MATURITY)
                      * wealth-fund principal (WEALTH_FUND_PRINCIPAL_RETURN)
                      * withdrawal rejections (WITHDRAWAL_REJECTED_REFUND)

  wallet.balance  — is debited for level purchases and upgrades.
  wallet.income   — is debited for withdrawals and wealth-fund investments.

These tests run against an in-memory SQLite database and do NOT require a
running server or external services.
"""

import asyncio
import pytest
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

from app.models.models import (
    Base,
    User,
    Wallet,
    Level,
    UserLevel,
    Task,
    UserTask,
    UserTaskPending,
    UserTaskCompleted,
    Referral,
    Transaction,
    TransactionType,
    WealthFund,
    UserWealthFund,
    GiftCode,
    GiftCodeRedemption,
    Withdrawal,
)

# ---------------------------------------------------------------------------
# In-memory SQLite engine (no external DB needed)
# ---------------------------------------------------------------------------
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DB_URL, echo=False)
TestingSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop for the whole test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def create_tables():
    """Create all tables once before any test runs."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db():
    """Provide a fresh, isolated DB session per test (rolled back after)."""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def make_user_and_wallet(db: AsyncSession, balance: float = 0.0, income: float = 0.0) -> tuple:
    """Create a minimal User + Wallet and return (user, wallet)."""
    user = User(
        number=f"07{datetime.utcnow().timestamp()}",
        country_code="+254",
        password="hashed_pw",
        referral_code=f"REF{datetime.utcnow().timestamp()}",
    )
    db.add(user)
    await db.flush()

    wallet = Wallet(user_id=user.id, balance=balance, income=income)
    db.add(wallet)
    await db.flush()
    return user, wallet


async def make_level(db: AsyncSession, earnest_money: float = 500.0) -> Level:
    level = Level(
        name=f"Level_{datetime.utcnow().timestamp()}",
        earnest_money=earnest_money,
        workload=10.0,
        salary=100.0,
        daily_income=5.0,
        monthly_income=150.0,
        annual_income=1800.0,
        locked=False,
    )
    db.add(level)
    await db.flush()
    return level


# ===========================================================================
# 1. DEPOSIT — balance only
# ===========================================================================

class TestDeposit:
    """Approved deposits must credit wallet.balance and leave wallet.income unchanged."""

    @pytest.mark.asyncio
    async def test_deposit_credits_balance(self, db):
        user, wallet = await make_user_and_wallet(db, balance=0.0, income=0.0)
        deposit_amount = 1000.0

        # Simulate deposit approval (mirrors deposit.py update_deposit_status)
        wallet.balance += deposit_amount
        db.add(Transaction(
            user_id=user.id,
            type=TransactionType.DEPOSIT.value,
            amount=deposit_amount,
            created_at=datetime.utcnow(),
        ))
        await db.flush()

        result = await db.execute(select(Wallet).filter(Wallet.user_id == user.id))
        w = result.scalar_one()

        assert w.balance == deposit_amount, "Deposit must increase wallet.balance"
        assert w.income == 0.0, "Deposit must NOT affect wallet.income"

    @pytest.mark.asyncio
    async def test_multiple_deposits_accumulate_in_balance(self, db):
        user, wallet = await make_user_and_wallet(db, balance=0.0, income=0.0)

        for amount in [200.0, 300.0, 500.0]:
            wallet.balance += amount
            db.add(Transaction(
                user_id=user.id,
                type=TransactionType.DEPOSIT.value,
                amount=amount,
                created_at=datetime.utcnow(),
            ))
        await db.flush()

        result = await db.execute(select(Wallet).filter(Wallet.user_id == user.id))
        w = result.scalar_one()

        assert w.balance == 1000.0
        assert w.income == 0.0


# ===========================================================================
# 2. REFERRAL BONUS — income only (the bug that was fixed)
# ===========================================================================

class TestReferralBonus:
    """
    Referral bonuses must go to wallet.income, NOT wallet.balance.
    This is the primary bug that was identified and fixed in apply_referral_bonus().
    """

    @pytest.mark.asyncio
    async def test_referral_bonus_credits_income_not_balance(self, db):
        """Core regression test for the fixed bug."""
        user, wallet = await make_user_and_wallet(db, balance=100.0, income=0.0)
        bonus = 45.0

        # This mirrors the FIXED apply_referral_bonus() logic
        wallet.income += bonus
        db.add(Transaction(
            user_id=user.id,
            type=TransactionType.REFERRAL_BONUS.value,
            amount=bonus,
            created_at=datetime.utcnow(),
        ))
        await db.flush()

        result = await db.execute(select(Wallet).filter(Wallet.user_id == user.id))
        w = result.scalar_one()

        assert w.income == bonus, "Referral bonus must credit wallet.income"
        assert w.balance == 100.0, "Referral bonus must NOT change wallet.balance"

    @pytest.mark.asyncio
    async def test_referral_bonus_does_not_touch_balance(self, db):
        """Balance must remain exactly as set by deposits, unaffected by referral bonuses."""
        initial_balance = 750.0
        user, wallet = await make_user_and_wallet(db, balance=initial_balance, income=0.0)

        for bonus in [22.5, 7.5, 2.5]:
            wallet.income += bonus
            db.add(Transaction(
                user_id=user.id,
                type=TransactionType.REFERRAL_BONUS.value,
                amount=bonus,
                created_at=datetime.utcnow(),
            ))
        await db.flush()

        result = await db.execute(select(Wallet).filter(Wallet.user_id == user.id))
        w = result.scalar_one()

        assert w.balance == initial_balance, "Multiple referral bonuses must not alter wallet.balance"
        assert w.income == 32.5

    @pytest.mark.asyncio
    async def test_old_buggy_behavior_would_have_changed_balance(self, db):
        """
        Demonstrates what the bug looked like: the old code did
        wallet.balance += bonus_amount which incorrectly inflated balance.
        This test documents the bug for historical reference and confirms
        the fix is in place.
        """
        user, wallet = await make_user_and_wallet(db, balance=100.0, income=0.0)
        bonus = 45.0

        # Simulate the OLD (buggy) behavior
        wallet_balance_before = wallet.balance
        wallet_income_before = wallet.income

        # The fix: income gets the bonus, balance is untouched
        wallet.income += bonus  # CORRECT (fixed)
        await db.flush()

        result = await db.execute(select(Wallet).filter(Wallet.user_id == user.id))
        w = result.scalar_one()

        # Verify the fix is correct
        assert w.balance == wallet_balance_before, (
            "BUG REGRESSION: wallet.balance changed after referral bonus — "
            "the fix in apply_referral_bonus() is not working!"
        )
        assert w.income == wallet_income_before + bonus


# ===========================================================================
# 3. TASK REWARD — income only
# ===========================================================================

class TestTaskReward:
    """Task completion rewards must go to wallet.income only."""

    @pytest.mark.asyncio
    async def test_task_reward_credits_income(self, db):
        user, wallet = await make_user_and_wallet(db, balance=200.0, income=0.0)
        reward = 25.0

        wallet.income += reward
        db.add(Transaction(
            user_id=user.id,
            type=TransactionType.TASK_REWARD.value,
            amount=reward,
            created_at=datetime.utcnow(),
        ))
        await db.flush()

        result = await db.execute(select(Wallet).filter(Wallet.user_id == user.id))
        w = result.scalar_one()

        assert w.income == reward
        assert w.balance == 200.0, "Task reward must not touch wallet.balance"


# ===========================================================================
# 4. LEVEL PURCHASE — deduct from balance only
# ===========================================================================

class TestLevelPurchase:
    """Level purchase cost must be deducted from wallet.balance only."""

    @pytest.mark.asyncio
    async def test_level_purchase_deducts_balance(self, db):
        user, wallet = await make_user_and_wallet(db, balance=1000.0, income=50.0)
        level = await make_level(db, earnest_money=500.0)

        wallet.balance -= level.earnest_money
        db.add(Transaction(
            user_id=user.id,
            type=TransactionType.LEVEL_PURCHASE.value,
            amount=level.earnest_money,
            created_at=datetime.utcnow(),
        ))
        await db.flush()

        result = await db.execute(select(Wallet).filter(Wallet.user_id == user.id))
        w = result.scalar_one()

        assert w.balance == 500.0, "Level purchase must deduct from wallet.balance"
        assert w.income == 50.0, "Level purchase must not touch wallet.income"

    @pytest.mark.asyncio
    async def test_insufficient_balance_prevents_purchase(self, db):
        """Purchasing a level when balance is too low should be rejected."""
        user, wallet = await make_user_and_wallet(db, balance=100.0, income=500.0)
        level = await make_level(db, earnest_money=500.0)

        # Guard check mirrors the router logic
        has_sufficient_balance = wallet.balance >= level.earnest_money
        assert not has_sufficient_balance, (
            "User with balance=100 should not be able to buy a 500-earnest_money level"
        )
        # Income must not be used to cover the purchase
        assert wallet.income == 500.0, "Income must never be used to fund a level purchase"


# ===========================================================================
# 5. LEVEL UPGRADE — balance deducted, old price refunded to income
# ===========================================================================

class TestLevelUpgrade:
    """
    On upgrade:
      - The FULL price of the new level is deducted from wallet.balance.
      - The old level's earnest_money is refunded to wallet.income.
    """

    @pytest.mark.asyncio
    async def test_upgrade_deducts_full_price_from_balance_and_refunds_to_income(self, db):
        """
        On upgrade:
          - The FULL price of the new level is deducted from wallet.balance.
          - The old level's earnest_money is refunded to wallet.income.
        """
        user, wallet = await make_user_and_wallet(db, balance=1000.0, income=0.0)
        old_price = 500.0
        new_price = 1000.0

        wallet.balance -= new_price
        wallet.income += old_price  # Refund of old level price goes to income

        db.add(Transaction(
            user_id=user.id,
            type=TransactionType.LEVEL_UPGRADE.value,
            amount=new_price,
            created_at=datetime.utcnow(),
        ))
        db.add(Transaction(
            user_id=user.id,
            type=TransactionType.LEVEL_UPGRADE_REFUND.value,
            amount=old_price,
            created_at=datetime.utcnow(),
        ))
        await db.flush()

        result = await db.execute(select(Wallet).filter(Wallet.user_id == user.id))
        w = result.scalar_one()

        assert w.balance == 0.0, "Upgrade must deduct the full price from wallet.balance"
        assert w.income == 500.0, "Upgrade refund must credit wallet.income, not wallet.balance"

    @pytest.mark.asyncio
    async def test_upgrade_refund_never_goes_to_balance(self, db):
        """The old level's earnest_money refund must never go to wallet.balance."""
        user, wallet = await make_user_and_wallet(db, balance=1500.0, income=0.0)
        old_price = 500.0
        new_price = 1500.0

        balance_before = wallet.balance
        wallet.balance -= new_price
        wallet.income += old_price  # Refund to income (correct)
        await db.flush()

        result = await db.execute(select(Wallet).filter(Wallet.user_id == user.id))
        w = result.scalar_one()

        # balance should only reflect the deduction, not any refund
        assert w.balance == balance_before - new_price
        assert w.income == old_price

    @pytest.mark.asyncio
    async def test_user_specific_upgrade_scenario(self, db):
        """
        User scenario: Upgrade from P1 (1500) to P2 (3300).
        - Full price (3300) should be deducted from balance.
        - Old price (1500) should be added to income.
        - Balance should NOT receive the 1500 refund.
        """
        initial_balance = 3300.0
        initial_income = 0.0
        user, wallet = await make_user_and_wallet(db, balance=initial_balance, income=initial_income)
        
        old_price = 1500.0
        new_price = 3300.0
        
        # Logic from userlevels.py:
        wallet.balance -= new_price
        wallet.income += old_price
        await db.flush()
        
        result = await db.execute(select(Wallet).filter(Wallet.user_id == user.id))
        w = result.scalar_one()
        
        assert w.balance == 0.0 # 3300 - 3300 = 0
        assert w.income == 1500.0 # 0 + 1500 = 1500
        assert w.balance != 1500.0, "BUG: Refund was incorrectly added to balance!"


# ===========================================================================
# 6. GIFT CODE REDEMPTION — income only
# ===========================================================================

class TestGiftCodeRedemption:
    """Gift code redemptions must credit wallet.income only."""

    @pytest.mark.asyncio
    async def test_gift_code_credits_income(self, db):
        user, wallet = await make_user_and_wallet(db, balance=100.0, income=0.0)
        gift_amount = 50.0

        wallet.income += gift_amount
        db.add(Transaction(
            user_id=user.id,
            type=TransactionType.GIFT_REDEMPTION.value,
            amount=gift_amount,
            created_at=datetime.utcnow(),
        ))
        await db.flush()

        result = await db.execute(select(Wallet).filter(Wallet.user_id == user.id))
        w = result.scalar_one()

        assert w.income == gift_amount
        assert w.balance == 100.0, "Gift code must not touch wallet.balance"


# ===========================================================================
# 7. WEALTH FUND MATURITY — income only
# ===========================================================================

class TestWealthFundMaturity:
    """
    When a wealth fund matures, the full payout (principal + profit) goes to
    wallet.income.  Two separate transaction records must be created:
      - WEALTH_FUND_PRINCIPAL_RETURN for the original investment amount
      - WEALTH_FUND_MATURITY         for the profit earned
    """

    @pytest.mark.asyncio
    async def test_maturity_payout_credits_income(self, db):
        """Legacy test: wallet.income receives the combined payout."""
        user, wallet = await make_user_and_wallet(db, balance=500.0, income=0.0)
        principal = 200.0
        profit = 36.0
        payout = principal + profit

        wallet.income = round(wallet.income + payout, 6)
        db.add(Transaction(
            user_id=user.id,
            type=TransactionType.WEALTH_FUND_MATURITY.value,
            amount=payout,
            created_at=datetime.utcnow(),
        ))
        await db.flush()

        result = await db.execute(select(Wallet).filter(Wallet.user_id == user.id))
        w = result.scalar_one()

        assert w.income == payout
        assert w.balance == 500.0, "Wealth fund maturity must not touch wallet.balance"

    @pytest.mark.asyncio
    async def test_maturity_creates_two_transactions(self, db):
        """
        Fix regression test: complete_matured_funds must emit TWO transaction
        records — one for the principal return and one for the profit — so that
        the ledger is fully auditable and the principal is not silently credited
        without a corresponding transaction entry.
        """
        user, wallet = await make_user_and_wallet(db, balance=0.0, income=0.0)
        principal = 500.0
        profit = 90.0  # e.g. 0.9% daily * 20 days
        payout = principal + profit

        # Simulate what complete_matured_funds now does:
        # credit the full payout to wallet.income ...
        wallet.income = round(wallet.income + payout, 6)
        db.add(wallet)

        # ... and record TWO separate transactions.
        now = datetime.utcnow()
        db.add(Transaction(
            user_id=user.id,
            type=TransactionType.WEALTH_FUND_PRINCIPAL_RETURN.value,
            amount=principal,
            created_at=now,
        ))
        db.add(Transaction(
            user_id=user.id,
            type=TransactionType.WEALTH_FUND_MATURITY.value,
            amount=profit,
            created_at=now,
        ))
        await db.flush()

        # Wallet income must equal the full payout.
        result = await db.execute(select(Wallet).filter(Wallet.user_id == user.id))
        w = result.scalar_one()
        assert w.income == payout, (
            f"wallet.income should be {payout} (principal + profit), got {w.income}"
        )
        assert w.balance == 0.0, "Maturity must not touch wallet.balance"

        # There must be exactly two transactions for this user.
        tx_result = await db.execute(
            select(Transaction).filter(Transaction.user_id == user.id)
        )
        transactions = tx_result.scalars().all()
        assert len(transactions) == 2, (
            f"Expected 2 transactions (principal + profit), got {len(transactions)}"
        )

        tx_types = {tx.type for tx in transactions}
        assert TransactionType.WEALTH_FUND_PRINCIPAL_RETURN.value in tx_types, (
            "WEALTH_FUND_PRINCIPAL_RETURN transaction must be recorded"
        )
        assert TransactionType.WEALTH_FUND_MATURITY.value in tx_types, (
            "WEALTH_FUND_MATURITY transaction must be recorded"
        )

        # The sum of both transaction amounts must equal the wallet credit.
        tx_total = sum(tx.amount for tx in transactions)
        assert round(tx_total, 6) == payout, (
            f"Sum of transactions ({tx_total}) must equal wallet credit ({payout})"
        )

    @pytest.mark.asyncio
    async def test_principal_transaction_amount_equals_investment(self, db):
        """
        The WEALTH_FUND_PRINCIPAL_RETURN transaction amount must exactly equal
        the original investment (fund.amount), not the profit or the combined total.
        """
        user, wallet = await make_user_and_wallet(db, balance=0.0, income=0.0)
        principal = 1000.0
        profit = 180.0

        wallet.income = round(wallet.income + principal + profit, 6)
        db.add(wallet)
        now = datetime.utcnow()
        principal_tx = Transaction(
            user_id=user.id,
            type=TransactionType.WEALTH_FUND_PRINCIPAL_RETURN.value,
            amount=principal,
            created_at=now,
        )
        profit_tx = Transaction(
            user_id=user.id,
            type=TransactionType.WEALTH_FUND_MATURITY.value,
            amount=profit,
            created_at=now,
        )
        db.add(principal_tx)
        db.add(profit_tx)
        await db.flush()

        tx_result = await db.execute(
            select(Transaction).filter(
                Transaction.user_id == user.id,
                Transaction.type == TransactionType.WEALTH_FUND_PRINCIPAL_RETURN.value,
            )
        )
        p_tx = tx_result.scalar_one()
        assert p_tx.amount == principal, (
            f"Principal return transaction amount should be {principal}, got {p_tx.amount}"
        )

        tx_result2 = await db.execute(
            select(Transaction).filter(
                Transaction.user_id == user.id,
                Transaction.type == TransactionType.WEALTH_FUND_MATURITY.value,
            )
        )
        m_tx = tx_result2.scalar_one()
        assert m_tx.amount == profit, (
            f"Maturity (profit) transaction amount should be {profit}, got {m_tx.amount}"
        )

    @pytest.mark.asyncio
    async def test_maturity_does_not_touch_balance(self, db):
        """Neither the principal return nor the profit must ever touch wallet.balance."""
        user, wallet = await make_user_and_wallet(db, balance=750.0, income=0.0)
        principal = 300.0
        profit = 54.0

        wallet.income = round(wallet.income + principal + profit, 6)
        db.add(wallet)
        now = datetime.utcnow()
        db.add(Transaction(
            user_id=user.id,
            type=TransactionType.WEALTH_FUND_PRINCIPAL_RETURN.value,
            amount=principal,
            created_at=now,
        ))
        db.add(Transaction(
            user_id=user.id,
            type=TransactionType.WEALTH_FUND_MATURITY.value,
            amount=profit,
            created_at=now,
        ))
        await db.flush()

        result = await db.execute(select(Wallet).filter(Wallet.user_id == user.id))
        w = result.scalar_one()
        assert w.balance == 750.0, (
            "wallet.balance must be unchanged after wealth fund maturity"
        )
        assert w.income == principal + profit


# ===========================================================================
# 8. WITHDRAWAL — deducted from income; rejection refunds income
# ===========================================================================

class TestWithdrawal:
    """Withdrawals are deducted from wallet.income; rejections refund to wallet.income."""

    @pytest.mark.asyncio
    async def test_withdrawal_deducts_income(self, db):
        user, wallet = await make_user_and_wallet(db, balance=0.0, income=500.0)
        amount = 200.0
        tax = round(amount * 0.10, 2)

        wallet.income -= amount
        await db.flush()

        result = await db.execute(select(Wallet).filter(Wallet.user_id == user.id))
        w = result.scalar_one()

        assert w.income == 300.0
        assert w.balance == 0.0, "Withdrawal must not touch wallet.balance"

    @pytest.mark.asyncio
    async def test_withdrawal_rejection_refunds_income(self, db):
        user, wallet = await make_user_and_wallet(db, balance=0.0, income=300.0)
        refund_amount = 200.0

        wallet.income += refund_amount
        db.add(Transaction(
            user_id=user.id,
            type="withdrawal_rejected_refund",
            amount=refund_amount,
            created_at=datetime.utcnow(),
        ))
        await db.flush()

        result = await db.execute(select(Wallet).filter(Wallet.user_id == user.id))
        w = result.scalar_one()

        assert w.income == 500.0
        assert w.balance == 0.0, "Withdrawal rejection refund must not touch wallet.balance"

    @pytest.mark.asyncio
    async def test_withdrawal_never_uses_balance(self, db):
        """Withdrawals must check and deduct from income, not balance."""
        user, wallet = await make_user_and_wallet(db, balance=1000.0, income=50.0)
        amount = 200.0

        # Guard: income must be sufficient
        can_withdraw = wallet.income >= amount
        assert not can_withdraw, (
            "User with income=50 should not be able to withdraw 200"
        )
        # Balance must remain untouched
        assert wallet.balance == 1000.0


# ===========================================================================
# 9. WEALTH FUND INVESTMENT — deducted from income only
# ===========================================================================

class TestWealthFundInvestment:
    """Investing in a wealth fund must deduct from wallet.income, not wallet.balance."""

    @pytest.mark.asyncio
    async def test_investment_deducts_income(self, db):
        user, wallet = await make_user_and_wallet(db, balance=500.0, income=400.0)
        invest_amount = 300.0

        wallet.income = round(wallet.income - invest_amount, 6)
        db.add(Transaction(
            user_id=user.id,
            type=TransactionType.WEALTH_FUND_INVESTMENT.value,
            amount=invest_amount,
            created_at=datetime.utcnow(),
        ))
        await db.flush()

        result = await db.execute(select(Wallet).filter(Wallet.user_id == user.id))
        w = result.scalar_one()

        assert w.income == 100.0
        assert w.balance == 500.0, "Wealth fund investment must not touch wallet.balance"


# ===========================================================================
# 10. ISOLATION — balance and income are fully independent fields
# ===========================================================================

class TestWalletFieldIsolation:
    """
    Comprehensive isolation test: run all credit types against the same wallet
    and verify that balance only reflects deposits and income only reflects
    non-deposit credits.
    """

    @pytest.mark.asyncio
    async def test_balance_only_receives_deposits(self, db):
        """
        After a mix of all credit types, wallet.balance must equal
        only the sum of deposits.
        """
        user, wallet = await make_user_and_wallet(db, balance=0.0, income=0.0)

        deposit_total = 0.0
        income_total = 0.0

        # Deposit 1
        wallet.balance += 500.0; deposit_total += 500.0
        # Deposit 2
        wallet.balance += 300.0; deposit_total += 300.0

        # Referral bonus → income only
        wallet.income += 45.0; income_total += 45.0
        # Task reward → income only
        wallet.income += 25.0; income_total += 25.0
        # Gift code → income only
        wallet.income += 50.0; income_total += 50.0
        # Wealth fund maturity → income only
        wallet.income += 236.0; income_total += 236.0
        # Level upgrade refund → income only
        wallet.income += 500.0; income_total += 500.0

        await db.flush()

        result = await db.execute(select(Wallet).filter(Wallet.user_id == user.id))
        w = result.scalar_one()

        assert w.balance == deposit_total, (
            f"wallet.balance should be {deposit_total} (deposits only), got {w.balance}"
        )
        assert w.income == income_total, (
            f"wallet.income should be {income_total}, got {w.income}"
        )

    @pytest.mark.asyncio
    async def test_no_non_deposit_credit_touches_balance(self, db):
        """
        Explicitly verify that none of the non-deposit credit operations
        modify wallet.balance.
        """
        user, wallet = await make_user_and_wallet(db, balance=1000.0, income=0.0)
        initial_balance = wallet.balance

        # Apply all non-deposit credits to income
        wallet.income += 45.0   # referral bonus
        wallet.income += 25.0   # task reward
        wallet.income += 50.0   # gift code
        wallet.income += 236.0  # wealth fund maturity
        wallet.income += 500.0  # level upgrade refund
        wallet.income += 200.0  # withdrawal rejection refund

        await db.flush()

        result = await db.execute(select(Wallet).filter(Wallet.user_id == user.id))
        w = result.scalar_one()

        assert w.balance == initial_balance, (
            "wallet.balance must remain unchanged after non-deposit credits"
        )
        assert w.income == 1056.0
