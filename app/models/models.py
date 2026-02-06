





from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    DateTime,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

# ==========================
# User
# ==========================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String, unique=True, nullable=False, index=True)
    country_code = Column(String, nullable=False)
    password = Column(String, nullable=False)

    referral_code = Column(String, unique=True, nullable=False, index=True)
    referred_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    is_admin = Column(Boolean, default=False)
    is_suspended = Column(Boolean, default=False)
    withdrawal_pin = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    referrer = relationship("User", remote_side=[id])

    wallet = relationship("Wallet", uselist=False, back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("UserTask", back_populates="user", cascade="all, delete-orphan")
    pending_tasks = relationship("UserTaskPending", back_populates="user", cascade="all, delete-orphan")
    completed_tasks = relationship("UserTaskCompleted", back_populates="user", cascade="all, delete-orphan")
    levels = relationship("UserLevel", back_populates="user", cascade="all, delete-orphan")
    wealthfunds = relationship("UserWealthFund", back_populates="user", cascade="all, delete-orphan")
    deposits = relationship("Deposit", back_populates="user", cascade="all, delete-orphan")
    withdrawals = relationship("Withdrawal", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    referrals_made = relationship("Referral", foreign_keys="Referral.referrer_id", back_populates="referrer", cascade="all, delete-orphan")
    referrals_received = relationship("Referral", foreign_keys="Referral.referred_id", back_populates="referred", cascade="all, delete-orphan")
    gift_redemptions = relationship(
        "GiftCodeRedemption",
        back_populates="user",
        cascade="all, delete-orphan"
    )


# ==========================
# Referrals
# ==========================
class Referral(Base):
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, index=True)

    referrer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    referred_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    level = Column(String, nullable=False)  # e.g., 'A', 'B', 'C', etc.
    is_active = Column(Boolean, default=False)
    bonus_amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    referrer = relationship("User", foreign_keys=[referrer_id], back_populates="referrals_made")
    referred = relationship("User", foreign_keys=[referred_id], back_populates="referrals_received")

    __table_args__ = (UniqueConstraint("referrer_id", "referred_id", name="_referrer_referred_uc"),)


# ==========================
# Wallet
# ==========================
class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    balance = Column(Float, default=0.0)
    income = Column(Float, default=0.0)

    user = relationship("User", back_populates="wallet")


# ==========================
# Levels
# ==========================
class Level(Base):
    __tablename__ = "levels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    earnest_money = Column(Float, default=0.0)
    workload = Column(Float, default=0.0)
    salary = Column(Float, default=0.0)
    daily_income = Column(Float, default=0.0)
    monthly_income = Column(Float, default=0.0)
    annual_income = Column(Float, default=0.0)
    locked = Column(Boolean, default=False)

    user_levels = relationship("UserLevel", back_populates="level", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="level", cascade="all, delete-orphan")


# ==========================
# Tasks
# ==========================
class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    reward = Column(Float, default=0.0)
    video_url = Column(String, nullable=False)
    level_id = Column(Integer, ForeignKey("levels.id", ondelete="CASCADE"), nullable=False)

    level = relationship("Level", back_populates="tasks")
    user_tasks = relationship("UserTask", back_populates="task", cascade="all, delete-orphan")
    pending_tasks = relationship("UserTaskPending", back_populates="task", cascade="all, delete-orphan")
    completed_tasks = relationship("UserTaskCompleted", back_populates="task", cascade="all, delete-orphan")


class UserTask(Base):
    __tablename__ = "user_tasks"
    __table_args__ = (UniqueConstraint("user_id", "task_id"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"))
    video_url = Column(String, nullable=False)
    completed = Column(Boolean, default=False)
    locked = Column(Boolean, default=False)
    description = Column(String, nullable=True)

    user = relationship("User", back_populates="tasks")
    task = relationship("Task", back_populates="user_tasks")


class UserTaskPending(Base):
    __tablename__ = "user_tasks_pending"
    __table_args__ = (UniqueConstraint("user_id", "task_id"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"))
    video_url = Column(String, nullable=False)
    pending_until = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="pending_tasks")
    task = relationship("Task", back_populates="pending_tasks")


class UserTaskCompleted(Base):
    __tablename__ = "user_tasks_completed"
    __table_args__ = (UniqueConstraint("user_id", "task_id"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"))
    video_url = Column(String, nullable=False)
    completed_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="completed_tasks")
    task = relationship("Task", back_populates="completed_tasks")


# ==========================
# User Levels
# ==========================
class UserLevel(Base):
    __tablename__ = "user_levels"
    __table_args__ = (UniqueConstraint("user_id", "level_id"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    level_id = Column(Integer, ForeignKey("levels.id", ondelete="CASCADE"))

    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    earnest_money = Column(Float, default=0.0)
    workload = Column(Float, default=0.0)
    salary = Column(Float, default=0.0)
    daily_income = Column(Float, default=0.0)
    monthly_income = Column(Float, default=0.0)
    annual_income = Column(Float, default=0.0)

    user = relationship("User", back_populates="levels")
    level = relationship("Level", back_populates="user_levels")


# ==========================
# Wealth Funds
# ==========================
class WealthFund(Base):
    __tablename__ = "wealthfunds"
    id = Column(Integer, primary_key=True, index=True)
    image = Column(String, nullable=True)
    name = Column(String, nullable=False, unique=True)
    profit_percent = Column(Float, nullable=False)
    duration_days = Column(Integer, nullable=False)
    daily_interest = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_wealthfunds = relationship(
        "UserWealthFund",
        back_populates="wealthfund",
        cascade="all, delete-orphan"
    )


class UserWealthFund(Base):
    __tablename__ = "user_wealthfunds"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    wealthfund_id = Column(Integer, ForeignKey("wealthfunds.id", ondelete="CASCADE"))
    image = Column(String, nullable=True)
    name = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    profit_percent = Column(Float, nullable=False)
    duration_days = Column(Integer, nullable=False)
    daily_interest = Column(Float, nullable=False)
    total_profit = Column(Float, default=0.0)
    today_interest = Column(Float, default=0.0)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=False)

    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="wealthfunds")
    wealthfund = relationship("WealthFund", back_populates="user_wealthfunds")


# ==========================
# Deposits / Withdrawals
# ==========================
class Deposit(Base):
    __tablename__ = "deposits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    name = Column(String, nullable=False)
    number = Column(String, nullable=False)
    account_number = Column(String, nullable=True)

    payment_method = Column(String, nullable=False)
    message = Column(String, nullable=True)
    amount = Column(Float, nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="deposits")


class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    name = Column(String, nullable=False)
    number = Column(String, nullable=False)

    amount = Column(Float, nullable=False)
    tax = Column(Float, nullable=False)
    net_amount = Column(Float, nullable=False)

    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="withdrawals")





from enum import Enum

class TransactionType(str, Enum):
    # Income (Credit)
    TASK_REWARD = "task_reward"
    REFERRAL_BONUS = "referral_bonus"
    WEALTH_FUND_MATURITY = "wealth_fund_maturity"
    REFERRAL_REBATE = "referral_rebate" 
    DEPOSIT = "deposit"
    COMMISSION = "commission"

    # Expenses (Debit)
    WEALTH_FUND_INVESTMENT = "wealth_fund_investment"
    WITHDRAWAL_REQUEST = "withdrawal_request"
    WITHDRAWAL_TAX = "withdrawal_tax"
    WITHDRAWAL_APPROVED = "withdrawal_approved"
    WITHDRAWAL_REJECTED_REFUND = "withdrawal_rejected_refund"
    LEVEL_PURCHASE = "level_purchase"
    LEVEL_UPGRADE = "level_upgrade"

# In your Transaction model
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    type = Column(String, nullable=False)  # Use TransactionType enum values
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="transactions")




# ==========================
# News
# ==========================
class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)    # News headline
    content = Column(String, nullable=False)  # Full news information
    created_at = Column(DateTime, default=datetime.utcnow)



# # ==========================
# # Gift Codes / Coupons
# # ==========================
# class GiftCode(Base):
#     __tablename__ = "gift_codes"

#     id = Column(Integer, primary_key=True, index=True)
#     code = Column(String, unique=True, nullable=False, index=True)  # the actual coupon code
#     amount = Column(Float, nullable=False)                          # value credited to user
#     is_active = Column(Boolean, default=True)                       # can the code be used
#     max_uses = Column(Integer, default=1)                            # max times the code can be used
#     expires_at = Column(DateTime, nullable=True)                     # optional expiry date
#     created_at = Column(DateTime, default=datetime.utcnow)

#     # Track which users redeemed this code
#     redemptions = relationship(
#         "GiftCodeRedemption",
#         back_populates="gift_code",
#         cascade="all, delete-orphan"
#     )


# class GiftCodeRedemption(Base):
#     __tablename__ = "gift_code_redemptions"
#     __table_args__ = (UniqueConstraint("user_id", "gift_code_id", name="_user_giftcode_uc"),)

#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
#     gift_code_id = Column(Integer, ForeignKey("gift_codes.id", ondelete="CASCADE"), nullable=False)
#     redeemed_at = Column(DateTime, default=datetime.utcnow)
#     amount_claimed = Column(Float, nullable=False)

#     user = relationship("User")
#     gift_code = relationship("GiftCode", back_populates="redemptions")

#     __table_args__ = (
#         UniqueConstraint("user_id", "gift_code_id", name="unique_user_giftcode"),
#     )








# ==========================
# Gift Codes / Coupons
# ==========================
class GiftCode(Base):
    __tablename__ = "gift_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False, index=True)  # the actual coupon code
    amount = Column(Float, nullable=False)                          # value credited to user
    is_active = Column(Boolean, default=True)                       # can the code be used
    max_uses = Column(Integer, default=1)                           # max times the code can be used
    expires_at = Column(DateTime, nullable=True)                    # optional expiry date
    created_at = Column(DateTime, default=datetime.utcnow)

    # Track which users redeemed this code
    redemptions = relationship(
        "GiftCodeRedemption",
        back_populates="gift_code",
        cascade="all, delete-orphan"
    )


# ==========================
# Gift Code Redemptions
# ==========================
class GiftCodeRedemption(Base):
    __tablename__ = "gift_code_redemptions"
    __table_args__ = (
        UniqueConstraint("user_id", "gift_code_id", name="unique_user_giftcode"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    gift_code_id = Column(Integer, ForeignKey("gift_codes.id", ondelete="CASCADE"), nullable=False)
    redeemed_at = Column(DateTime, default=datetime.utcnow)
    amount_claimed = Column(Float, nullable=False)

    # Relationships
    user = relationship("User", back_populates="gift_redemptions")  # new relationship
    gift_code = relationship("GiftCode", back_populates="redemptions")
