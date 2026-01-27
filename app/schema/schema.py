# schemas.py
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class UserCreate(BaseModel):
    number: str
    password: str
    country_code: str
    referral: str | None = None

class UserLogin(BaseModel):
    number: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str








# ==========================
# User Schemas
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

# --------------------------
# Register / Login Schemas
# --------------------------
class UserCreate(BaseModel):
    number: str
    country_code: str
    password: str
    referral: Optional[str] = None  # referral code

class Token(BaseModel):
    access_token: str
    token_type: str

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

# ==========================
# Withdrawal Schemas
# ==========================
class WithdrawalCreate(BaseModel):
    amount: float

class WithdrawalResponse(BaseModel):
    id: int
    user_id: int
    amount: float
    created_at: datetime

    class Config:
        orm_mode = True

# ==========================
# Admin Filters / Responses
# ==========================
class DepositsListResponse(BaseModel):
    deposits: List[DepositResponse]

class TransactionsListResponse(BaseModel):
    transactions: List[TransactionResponse]

class UsersListResponse(BaseModel):
    users: List[UserResponse]





class SetWithdrawalPin(BaseModel):
    pin: str


class ChangeWithdrawalPin(BaseModel):
    old_pin: str
    new_pin: str




from pydantic import BaseModel
from datetime import datetime


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
