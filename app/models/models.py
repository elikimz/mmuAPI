from sqlalchemy import Boolean, Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime, timedelta

Base = declarative_base()

# ==========================
# User Model
# ==========================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String, unique=True, nullable=False)
    country_code = Column(String, nullable=False) 
    password = Column(String, nullable=False)
    referral_code = Column(String, unique=True, nullable=False)  # auto-generated
    referred_by = Column(String, nullable=True)  
    is_admin = Column(Boolean, default=False)
    is_suspended = Column(Boolean, default=False)


    wallet = relationship("Wallet", uselist=False, back_populates="user")
    tasks = relationship("UserTask", back_populates="user")
    pending_tasks = relationship("UserTaskPending", back_populates="user")
    completed_tasks = relationship("UserTaskCompleted", back_populates="user")
    levels = relationship("UserLevel", back_populates="user")
    wealthfunds = relationship("UserWealthFund", back_populates="user")
    deposits = relationship("Deposit", back_populates="user")
    withdrawals = relationship("Withdrawal", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")

# ==========================
# Wallet Model
# ==========================
class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    balance = Column(Float, default=0.0)
    income = Column(Float, default=0.0)

    user = relationship("User", back_populates="wallet")

# ==========================
# Levels Models
# ==========================
class Level(Base):
    __tablename__ = "levels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    earnest_money = Column(Float, default=0.0)
    workload = Column(Float, default=0.0)
    salary = Column(Float, default=0.0)
    daily_income = Column(Float, default=0.0)
    monthly_income = Column(Float, default=0.0)
    annual_income = Column(Float, default=0.0)

    user_levels = relationship("UserLevel", back_populates="level")
    tasks = relationship("Task", back_populates="level", cascade="all, delete-orphan")

# ==========================
# Tasks Models
# ==========================
class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    reward = Column(Float, default=0.0)
    video_url = Column(String, nullable=False)
    level_id = Column(Integer, ForeignKey("levels.id"), nullable=False)
    completed = Column(Boolean, nullable=True, default=None)

    level = relationship("Level", back_populates="tasks")
    user_tasks = relationship("UserTask", back_populates="task", cascade="all, delete-orphan")
    pending_tasks = relationship("UserTaskPending", back_populates="task", cascade="all, delete-orphan")
    completed_tasks = relationship("UserTaskCompleted", back_populates="task", cascade="all, delete-orphan")

class UserTask(Base):
    __tablename__ = "user_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    task_id = Column(Integer, ForeignKey("tasks.id"))
    video_url = Column(String, nullable=False)
    completed = Column(Boolean, nullable=True, default=False)

    user = relationship("User", back_populates="tasks")
    task = relationship("Task", back_populates="user_tasks")

# ==========================
# UserTaskPending Model
# ==========================
class UserTaskPending(Base):
    __tablename__ = "user_tasks_pending"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    video_url = Column(String, nullable=False)
    pending_until = Column(DateTime, nullable=False)  # When the pending period ends
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="pending_tasks")
    task = relationship("Task", back_populates="pending_tasks")

# ==========================
# UserTaskCompleted Model
# ==========================
class UserTaskCompleted(Base):
    __tablename__ = "user_tasks_completed"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    video_url = Column(String, nullable=False)
    completed_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="completed_tasks")
    task = relationship("Task", back_populates="completed_tasks")

# ==========================
# UserLevel Model
# ==========================
class UserLevel(Base):
    __tablename__ = "user_levels"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    level_id = Column(Integer, ForeignKey("levels.id"))
    name = Column(String, nullable=False)
    earnest_money = Column(Float, default=0.0)
    workload = Column(Float, default=0.0)
    salary = Column(Float, default=0.0)
    daily_income = Column(Float, default=0.0)
    monthly_income = Column(Float, default=0.0)
    annual_income = Column(Float, default=0.0)


    user = relationship("User", back_populates="levels")
    level = relationship("Level", back_populates="user_levels")

# ==========================
# Wealth Fund Models
# ==========================
class WealthFund(Base):
    __tablename__ = "wealthfunds"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    duration_days = Column(Integer, nullable=False)
    daily_interest = Column(Float, nullable=False)

    user_wealthfunds = relationship("UserWealthFund", back_populates="wealthfund")

class UserWealthFund(Base):
    __tablename__ = "user_wealthfunds"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    wealthfund_id = Column(Integer, ForeignKey("wealthfunds.id"))
    name = Column(String, nullable=False)
    duration_days = Column(Integer, nullable=False)
    daily_interest = Column(Float, nullable=False)

    user = relationship("User", back_populates="wealthfunds")
    wealthfund = relationship("WealthFund", back_populates="user_wealthfunds")

# ==========================
# Deposits & Withdrawals
# ==========================
class Deposit(Base):
    __tablename__ = "deposits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="deposits")

class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="withdrawals")

# ==========================
# Transactions (GLOBAL LEDGER)
# ==========================
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="transactions")
