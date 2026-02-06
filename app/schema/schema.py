# # schemas.py
# from dataclasses import Field
# from datetime import datetime
# from typing import List, Optional
# from pydantic import BaseModel

# class UserCreate(BaseModel):
#     number: str
#     password: str
#     country_code: str
#     referral: str | None = None

# class UserLogin(BaseModel):
#     number: str
#     password: str

# class Token(BaseModel):
#     access_token: str
#     token_type: str








# # ==========================
# # User Schemas
# # ==========================
# class UserBase(BaseModel):
#     number: str
#     country_code: str
#     is_admin: bool
#     is_suspended: bool
#     referral_code: str
#     referred_by: Optional[int]

# class UserResponse(UserBase):
#     id: int

#     class Config:
#         orm_mode = True

# # --------------------------
# # Register / Login Schemas
# # --------------------------
# class UserCreate(BaseModel):
#     number: str
#     country_code: str
#     password: str
#     referral: Optional[str] = None  # referral code

# class Token(BaseModel):
#     access_token: str
#     token_type: str

# # ==========================
# # Deposit Schemas
# # ==========================
# class DepositCreate(BaseModel):
#     payment_method: str               # e.g., "Mpesa" or "Airtel"
#     amount: float
#     message: Optional[str] = None
#     account_number: Optional[str] = None
#     name: str                          # user's name at deposit time
#     number: str                        # user's phone number at deposit time

# class DepositUpdateStatus(BaseModel):
#     status: str                       # "approved", "canceled", "pending"

# class DepositResponse(BaseModel):
#     id: int
#     user_id: int
#     name: str
#     number: str
#     account_number: Optional[str]
#     payment_method: str
#     message: Optional[str]
#     amount: float
#     status: str
#     created_at: datetime

#     class Config:
#         orm_mode = True

# # ==========================
# # Transaction Schemas
# # ==========================
# class TransactionCreate(BaseModel):
#     user_id: int
#     type: str                        # e.g., "deposit", "withdrawal"
#     amount: float

# class TransactionResponse(BaseModel):
#     id: int
#     user_id: int
#     type: str
#     amount: float
#     created_at: datetime

#     class Config:
#         orm_mode = True

# # ==========================
# # Withdrawal Schemas
# # ==========================
# class WithdrawalCreate(BaseModel):
#     amount: float

# class WithdrawalResponse(BaseModel):
#     id: int
#     user_id: int
#     amount: float
#     created_at: datetime

#     class Config:
#         orm_mode = True

# # ==========================
# # Admin Filters / Responses
# # ==========================
# class DepositsListResponse(BaseModel):
#     deposits: List[DepositResponse]

# class TransactionsListResponse(BaseModel):
#     transactions: List[TransactionResponse]

# class UsersListResponse(BaseModel):
#     users: List[UserResponse]





# class SetWithdrawalPin(BaseModel):
#     pin: str


# class ChangeWithdrawalPin(BaseModel):
#     old_pin: str
#     new_pin: str




# from pydantic import BaseModel
# from datetime import datetime


# class WithdrawalCreate(BaseModel):
#     name: str
#     number: str
#     amount: float
#     pin: str


# class WithdrawalUpdateStatus(BaseModel):
#     status: str  # approved | rejected


# class WithdrawalResponse(BaseModel):
#     id: int
#     user_id: int
#     name: str
#     number: str
#     amount: float
#     tax: float
#     net_amount: float
#     status: str
#     created_at: datetime

#     class Config:
#         from_attributes = True





# from pydantic import BaseModel
# from typing import Optional

# # -------------------------
# # CREATE
# # -------------------------
# class LevelCreate(BaseModel):
#     name: str
#     description: Optional[str] = None 
#     earnest_money: float = 0.0
#     workload: float = 0.0
#     salary: float = 0.0
#     daily_income: float = 0.0
#     monthly_income: float = 0.0
#     annual_income: float = 0.0
#     locked: Optional[bool] = False  # 👈 new field, default unlocked

# # -------------------------
# # UPDATE
# # -------------------------
# class LevelUpdate(BaseModel):
#     name: Optional[str] = None
#     description: Optional[str] = None 
#     earnest_money: Optional[float] = None
#     workload: Optional[float] = None
#     salary: Optional[float] = None
#     daily_income: Optional[float] = None
#     monthly_income: Optional[float] = None
#     annual_income: Optional[float] = None
#     locked: Optional[bool] = None  # 👈 new field, can lock/unlock

# # -------------------------
# # RESPONSE
# # -------------------------
# class LevelResponse(BaseModel):
#     id: int
#     name: str
#     description: Optional[str] = None 
#     earnest_money: float
#     workload: float
#     salary: float
#     daily_income: float
#     monthly_income: float
#     annual_income: float
#     task_count: int   # 👈 dynamically calculated
#     locked: bool      # 👈 new field in response

#     class Config:
#         orm_mode = True





# # -------------------------
# # CREATE
# # -------------------------
# class TaskCreate(BaseModel):
#     level_id: int
#     name: str
#     reward: float = 0.0
#     video_url: str


# # -------------------------
# # UPDATE
# # -------------------------
# class TaskUpdate(BaseModel):
#     name: Optional[str] = None
#     reward: Optional[float] = None
#     video_url: Optional[str] = None
#     level_id: Optional[int] = None


# # -------------------------
# # RESPONSE
# # -------------------------
# class TaskResponse(BaseModel):
#     id: int
#     name: str
#     reward: float
#     video_url: str
#     level_id: int

#     class Config:
#         orm_mode = True





# # -------------------------
# # CREATE / BUY LEVEL
# # -------------------------
# class BuyLevelRequest(BaseModel):
#     level_id: int


# # -------------------------
# # RESPONSE
# # -------------------------
# class UserLevelResponse(BaseModel):
#     id: int
#     level_id: int
#     name: str
#     description: Optional[str]
#     earnest_money: float
#     workload: float
#     salary: float
#     daily_income: float
#     monthly_income: float
#     annual_income: float

#     class Config:
#         orm_mode = True


# # -------------------------
# # LEVEL INFO (PUBLIC)
# # -------------------------
# class LevelInfoResponse(BaseModel):
#     id: int
#     name: str
#     description: Optional[str]
#     earnest_money: float
#     workload: float
#     salary: float
#     daily_income: float
#     monthly_income: float
#     annual_income: float

#     class Config:
#         orm_mode = True





# # -------------------------
# # Response for User Task (includes reward)
# # -------------------------
# class UserTaskResponse(BaseModel):
#     id: int
#     user_id: int
#     task_id: int
#     video_url: str
#     completed: bool
#     locked: Optional[bool] = False  
#     reward: float
#     description: Optional[str]
#     level_name: str 


#     class Config:
#         orm_mode = True

# # -------------------------
# # Response for Pending Task
# # -------------------------
# class UserTaskPendingResponse(BaseModel):
#     id: int
#     user_id: int
#     task_id: int
#     video_url: str
#     pending_until: datetime
#     created_at: datetime
#     reward: float  # Include reward for pending tasks
#     level_name: str 

#     class Config:
#         orm_mode = True

# # -------------------------
# # Response for Completed Task
# # -------------------------
# class UserTaskCompletedResponse(BaseModel):
#     id: int
#     user_id: int
#     task_id: int
#     video_url: str
#     completed_at: datetime
#     reward: float  # Include reward for completed tasks
#     level_name: str 

#     class Config:
#         orm_mode = True

# # -------------------------
# # Request to complete a task
# # -------------------------
# class CompleteTaskRequest(BaseModel):
#     user_task_id: int





# from pydantic import BaseModel
# from typing import Optional
# from datetime import datetime

# # =========================
# # WealthFund Schemas
# # =========================

# class WealthFundCreate(BaseModel):
#     image: Optional[str] = None
#     name: str
#     profit_percent: float
#     duration_days: int
#     daily_interest: float

# class WealthFundUpdate(BaseModel):
#     image: Optional[str] = None
#     name: Optional[str] = None
#     profit_percent: Optional[float] = None
#     duration_days: Optional[int] = None
#     daily_interest: Optional[float] = None

# class WealthFundResponse(BaseModel):
#     id: int
#     image: Optional[str]
#     name: str
#     profit_percent: float
#     duration_days: int
#     daily_interest: float

#     class Config:
#         orm_mode = True

# # =========================
# # User WealthFund Schemas
# # =========================

# class InvestWealthFundRequest(BaseModel):
#     wealthfund_id: int
#     amount: float  # User's investment amount

# class UserWealthFundResponse(BaseModel):
#     id: int
#     wealthfund_id: int

#     image: Optional[str]
#     name: str
#     amount: float  # User's investment amount
#     profit_percent: float
#     duration_days: int
#     daily_interest: float

#     total_profit: float
#     today_interest: float

#     start_date: datetime
#     end_date: datetime
#     status: str
#     created_at: datetime

#     class Config:
#         orm_mode = True






# class ReferredUserLevelResponse(BaseModel):
#     name: str
#     earnest_money: float
#     salary: float
#     daily_income: float
#     monthly_income: float
#     annual_income: float

#     class Config:
#         orm_mode = True


# class ReferredUserResponse(BaseModel):
#     id: int
#     number: str
#     country_code: str
#     referral_code: str   # ✅ HERE
#     created_at: datetime
#     level: Optional[ReferredUserLevelResponse]

#     class Config:
#         orm_mode = True


# class MyReferralResponse(BaseModel):
#     id: int
#     level: str
#     is_active: bool
#     bonus_amount: float
#     created_at: datetime
#     referred_user: ReferredUserResponse

#     class Config:
#         orm_mode = True








# class WalletResponse(BaseModel):
#     balance: float
#     income: float


# class LevelResponse(BaseModel):
#     id: int
#     name: str
#     daily_income: float
#     monthly_income: float


# class WealthFundResponse(BaseModel):
#     id: int
#     name: str
#     amount: float
#     total_profit: float
#     status: str


# class UserProfileResponse(BaseModel):
#     id: int
#     number: str
#     country_code: str
#     referral_code: str
#     created_at: datetime

#     wallet: Optional[WalletResponse]
#     levels: List[LevelResponse]

#     total_tasks: int
#     completed_tasks: int
#     pending_tasks: int

#     total_referrals: int
#     active_referrals: int
#     referral_bonus: float

#     wealthfunds: List[WealthFundResponse]




# from pydantic import BaseModel, Field
# from datetime import datetime
# from typing import Optional

# # ==========================
# # Gift Code Schemas
# # ==========================
# class GiftCodeCreate(BaseModel):
#     code: str
#     amount: float
#     is_active: bool = True
#     max_uses: int = 1
   

# class GiftCodeRead(BaseModel):
#     id: int
#     code: str
#     amount: float
#     is_active: bool
#     max_uses: int
#     expires_at: Optional[datetime]
#     created_at: datetime

#     class Config:
#         orm_mode = True

# class GiftCodeRedeem(BaseModel):
#     code: str






# # --------------------------
# # Reward Schemas
# # --------------------------
# class SpinWheelRewardBase(BaseModel):
#     name: str
#     amount: float
#     weight: Optional[float] = 1.0
#     is_active: Optional[bool] = True

# class SpinWheelRewardCreate(SpinWheelRewardBase):
#     pass

# class SpinWheelRewardRead(SpinWheelRewardBase):
#     id: int
#     created_at: datetime

#     model_config = {
#         "from_attributes": True  # ✅ Required for SQLAlchemy v2 async
#     }

# # --------------------------
# # User Spin Schemas
# # --------------------------
# class UserSpinRead(BaseModel):
#     id: int
#     reward: SpinWheelRewardRead
#     created_at: datetime

#     model_config = {
#         "from_attributes": True  # ✅ Required for nested ORM objects
#     }

# # --------------------------
# # Spin Wheel Config Schemas
# # --------------------------
# class SpinWheelConfigBase(BaseModel):
#     max_spins_per_day: int = 1
#     is_active: bool = True

# class SpinWheelConfigRead(SpinWheelConfigBase):
#     id: int
#     created_at: datetime

#     model_config = {
#         "from_attributes": True
#     }







from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

# ==========================
# User & Auth Schemas
# ==========================
class UserBase(BaseModel):
    number: str
    country_code: str
    is_admin: bool
    is_suspended: bool
    referral_code: str
    referred_by: Optional[int]

class UserResponse(UserBase):
    id: int

    class Config:
        orm_mode = True

class UserCreate(BaseModel):
    number: str
    country_code: str
    password: str
    referral: Optional[str] = None  # referral code

class UserLogin(BaseModel):
    number: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# ==========================
# Wallet Schemas
# ==========================
class WalletResponse(BaseModel):
    balance: float
    income: float

# ==========================
# Deposit Schemas
# ==========================
class DepositCreate(BaseModel):
    payment_method: str               # e.g., "Mpesa" or "Airtel"
    amount: float
    message: Optional[str] = None
    account_number: Optional[str] = None
    name: str                          # user's name at deposit time
    number: str                        # user's phone number at deposit time

class DepositUpdateStatus(BaseModel):
    status: str                       # "approved", "canceled", "pending"

class DepositResponse(BaseModel):
    id: int
    user_id: int
    name: str
    number: str
    account_number: Optional[str]
    payment_method: str
    message: Optional[str]
    amount: float
    status: str
    created_at: datetime

    class Config:
        orm_mode = True

class DepositsListResponse(BaseModel):
    deposits: List[DepositResponse]

# ==========================
# Withdrawal Schemas
# ==========================
class WithdrawalCreate(BaseModel):
    name: str
    number: str
    amount: float
    pin: str

class WithdrawalUpdateStatus(BaseModel):
    status: str  # approved | rejected

class WithdrawalResponse(BaseModel):
    id: int
    user_id: int
    name: str
    number: str
    amount: float
    tax: float
    net_amount: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

# ==========================
# Transaction Schemas
# ==========================
class TransactionCreate(BaseModel):
    user_id: int
    type: str                        # e.g., "deposit", "withdrawal"
    amount: float

class TransactionResponse(BaseModel):
    id: int
    user_id: int
    type: str
    amount: float
    created_at: datetime

    class Config:
        orm_mode = True

class TransactionsListResponse(BaseModel):
    transactions: List[TransactionResponse]

# ==========================
# Level Schemas
# ==========================
class LevelCreate(BaseModel):
    name: str
    description: Optional[str] = None
    earnest_money: float = 0.0
    workload: float = 0.0
    salary: float = 0.0
    daily_income: float = 0.0
    monthly_income: float = 0.0
    annual_income: float = 0.0
    locked: Optional[bool] = False

class LevelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    earnest_money: Optional[float] = None
    workload: Optional[float] = None
    salary: Optional[float] = None
    daily_income: Optional[float] = None
    monthly_income: Optional[float] = None
    annual_income: Optional[float] = None
    locked: Optional[bool] = None

class LevelResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    earnest_money: float
    workload: float
    salary: float
    daily_income: float
    monthly_income: float
    annual_income: float
    task_count: int
    locked: bool

    class Config:
        orm_mode = True

class LevelInfoResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    earnest_money: float
    workload: float
    salary: float
    daily_income: float
    monthly_income: float
    annual_income: float

    class Config:
        orm_mode = True

# ==========================
# User Level Schemas
# ==========================
class BuyLevelRequest(BaseModel):
    level_id: int

class UserLevelResponse(BaseModel):
    id: int
    level_id: int
    name: str
    description: Optional[str]
    earnest_money: float
    workload: float
    salary: float
    daily_income: float
    monthly_income: float
    annual_income: float

    class Config:
        orm_mode = True

# ==========================
# Task Schemas
# ==========================
class TaskCreate(BaseModel):
    level_id: int
    name: str
    reward: float = 0.0
    video_url: str

class TaskUpdate(BaseModel):
    name: Optional[str] = None
    reward: Optional[float] = None
    video_url: Optional[str] = None
    level_id: Optional[int] = None

class TaskResponse(BaseModel):
    id: int
    name: str
    reward: float
    video_url: str
    level_id: int

    class Config:
        orm_mode = True

class UserTaskResponse(BaseModel):
    id: int
    user_id: int
    task_id: int
    video_url: str
    completed: bool
    locked: Optional[bool] = False
    reward: float
    description: Optional[str]
    level_name: str

    class Config:
        orm_mode = True

class UserTaskPendingResponse(BaseModel):
    id: int
    user_id: int
    task_id: int
    video_url: str
    pending_until: datetime
    created_at: datetime
    reward: float
    level_name: str

    class Config:
        orm_mode = True

class UserTaskCompletedResponse(BaseModel):
    id: int
    user_id: int
    task_id: int
    video_url: str
    completed_at: datetime
    reward: float
    level_name: str

    class Config:
        orm_mode = True

class CompleteTaskRequest(BaseModel):
    user_task_id: int

# ==========================
# Wealth Fund Schemas
# ==========================
class WealthFundCreate(BaseModel):
    image: Optional[str] = None
    name: str
    profit_percent: float
    duration_days: int
    daily_interest: float

class WealthFundUpdate(BaseModel):
    image: Optional[str] = None
    name: Optional[str] = None
    profit_percent: Optional[float] = None
    duration_days: Optional[int] = None
    daily_interest: Optional[float] = None

class WealthFundResponse(BaseModel):
    id: int
    image: Optional[str]
    name: str
    profit_percent: float
    duration_days: int
    daily_interest: float

    class Config:
        orm_mode = True

class InvestWealthFundRequest(BaseModel):
    wealthfund_id: int
    amount: float  # User's investment amount

class UserWealthFundResponse(BaseModel):
    id: int
    wealthfund_id: int
    image: Optional[str]
    name: str
    amount: float
    profit_percent: float
    duration_days: int
    daily_interest: float
    total_profit: float
    today_interest: float
    start_date: datetime
    end_date: datetime
    status: str
    created_at: datetime

    class Config:
        orm_mode = True

# ==========================
# Referral Schemas
# ==========================
class ReferredUserLevelResponse(BaseModel):
    name: str
    earnest_money: float
    salary: float
    daily_income: float
    monthly_income: float
    annual_income: float

    class Config:
        orm_mode = True

class ReferredUserResponse(BaseModel):
    id: int
    number: str
    country_code: str
    referral_code: str
    created_at: datetime
    level: Optional[ReferredUserLevelResponse]

    class Config:
        orm_mode = True

class MyReferralResponse(BaseModel):
    id: int
    level: str
    is_active: bool
    bonus_amount: float
    created_at: datetime
    referred_user: ReferredUserResponse

    class Config:
        orm_mode = True

# ==========================
# User Profile Schema
# ==========================
class UserProfileResponse(BaseModel):
    id: int
    number: str
    country_code: str
    referral_code: str
    created_at: datetime
    wallet: Optional[WalletResponse]
    levels: List[LevelResponse]
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    total_referrals: int
    active_referrals: int
    referral_bonus: float
    wealthfunds: List[WealthFundResponse]

# ==========================
# Gift Code Schemas
# ==========================
class GiftCodeCreate(BaseModel):
    code: str
    amount: float
    is_active: bool = True
    max_uses: int = 1

class GiftCodeRead(BaseModel):
    id: int
    code: str
    amount: float
    is_active: bool
    max_uses: int
    expires_at: Optional[datetime]
    created_at: datetime

    class Config:
        orm_mode = True

class GiftCodeRedeem(BaseModel):
    code: str

# ==========================
# Spin Wheel Schemas
# ==========================
class SpinWheelRewardBase(BaseModel):
    name: str
    amount: float
    weight: Optional[float] = 1.0
    is_active: Optional[bool] = True

class SpinWheelRewardCreate(SpinWheelRewardBase):
    pass

class SpinWheelRewardRead(SpinWheelRewardBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class UserSpinRead(BaseModel):
    id: int
    reward: SpinWheelRewardRead
    created_at: datetime

    class Config:
        from_attributes = True

class SpinWheelConfigBase(BaseModel):
    max_spins_per_day: int = 1
    is_active: bool = True

class SpinWheelConfigRead(SpinWheelConfigBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# ==========================
# Pin Schemas
# ==========================
class SetWithdrawalPin(BaseModel):
    pin: str

class ChangeWithdrawalPin(BaseModel):
    old_pin: str
    new_pin: str
