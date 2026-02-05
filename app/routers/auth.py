


from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import random
import string

from app.database.database import get_async_db
from app.models.models import User, Wallet
from app.core.jwt import hash_password, verify_password, create_access_token, decode_access_token
from app.schema.schema import UserCreate, Token

router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ------------------------
# Helper: generate referral code
# ------------------------
def generate_referral_code(length: int = 6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


# ------------------------
# REGISTER
# ------------------------


# Define a response model for success messages
class SuccessResponse(BaseModel):
    message: str





@router.post(
    "/register",
    response_model=SuccessResponse,
    status_code=201,
)
async def register(user: UserCreate, db: AsyncSession = Depends(get_async_db)):
    full_number = f"{user.country_code}{user.number}"

    # -------------------------
    # 1. Check if user exists
    # -------------------------
    result = await db.execute(select(User).where(User.number == full_number))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already exists")

    # -------------------------
    # 2. Generate unique referral code
    # -------------------------
    while True:
        referral_code = generate_referral_code()
        result = await db.execute(select(User).where(User.referral_code == referral_code))
        if not result.scalar_one_or_none():
            break

    # -------------------------
    # 3. Validate referral
    # -------------------------
    referred_by = None
    ref_user = None
    if user.referral:
        result = await db.execute(select(User).where(User.referral_code == user.referral))
        ref_user = result.scalar_one_or_none()
        if not ref_user:
            raise HTTPException(status_code=400, detail="Invalid referral code")
        referred_by = ref_user.id

    # -------------------------
    # 4. First user becomes admin
    # -------------------------
    result = await db.execute(select(User.id).limit(1))
    is_first_user = result.scalar_one_or_none() is None

    # -------------------------
    # 5. Create the new user
    # -------------------------
    new_user = User(
        number=full_number,
        country_code=user.country_code,
        password=hash_password(user.password),
        referral_code=referral_code,
        referred_by=referred_by,
        is_admin=is_first_user,
        is_suspended=False
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # -------------------------
    # 6. Create wallet
    # -------------------------
    wallet = Wallet(
        user_id=new_user.id,
        balance=0.0,
        income=0.0
    )
    db.add(wallet)
    await db.commit()

    # -------------------------
    # 7. Handle multi-level referrals (A/B/C)
    # -------------------------
    if ref_user:
        from app.models.models import Referral

        levels = ["A", "B", "C"]
        current_referrer = ref_user

        for level in levels:
            if not current_referrer:
                break

            referral_record = Referral(
                referrer_id=current_referrer.id,
                referred_id=new_user.id,
                level=level,
                is_active=False,
                bonus_amount=0.0
            )
            db.add(referral_record)
            await db.commit()

            # Move to next level referrer (parent of current_referrer)
            if current_referrer.referred_by is None:
                break

            result = await db.execute(select(User).where(User.id == current_referrer.referred_by))
            current_referrer = result.scalar_one_or_none()

    return {"message": "User registered successfully."}








# ------------------------
# LOGIN
# ------------------------
def normalize_number(number: str):
    if number.startswith("0"):
        return "+254" + number[1:]
    return number

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_async_db)):
    full_number = normalize_number(form_data.username)

    result = await db.execute(select(User).filter(User.number == full_number))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if getattr(user, "is_suspended", False):
        raise HTTPException(status_code=403, detail="Your account has been suspended. Please contact support.")

    access_token = create_access_token({"sub": user.number, "user_id": user.id ,"is_admin": getattr(user, "is_admin", False)})
    return {"access_token": access_token, "token_type": "bearer"}


# ------------------------
# GET CURRENT USER
# ------------------------
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_async_db)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    number = payload.get("sub")
    result = await db.execute(select(User).filter(User.number == number))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "number": current_user.number,
        "country_code": current_user.country_code,
        "referral_code": current_user.referral_code,
        "referred_by": current_user.referred_by,
        "is_admin": getattr(current_user, "is_admin", False),
        "is_suspended": getattr(current_user, "is_suspended", False)
    }


# ==========================
# ADMIN ROUTES
# ==========================

async def get_current_admin(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_async_db)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    number = payload.get("sub")
    result = await db.execute(select(User).filter(User.number == number))
    admin = result.scalar_one_or_none()
    if not admin or not getattr(admin, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    return admin


# GET ALL USERS
@router.get("/admin/users")
async def get_all_users(admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [
        {
            "id": user.id,
            "number": user.number,
            "country_code": user.country_code,
            "referral_code": user.referral_code,
            "referred_by": user.referred_by,
            "is_admin": getattr(user, "is_admin", False),
            "is_suspended": getattr(user, "is_suspended", False)
        } for user in users
    ]


# SUSPEND / UNSUSPEND USER
@router.patch("/admin/users/{user_id}/suspend")
async def suspend_user(user_id: int, suspend: bool, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    setattr(user, "is_suspended", suspend)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"id": user.id, "number": user.number, "is_suspended": getattr(user, "is_suspended", False)}


# CHANGE USER PASSWORD
@router.patch("/admin/users/{user_id}/password")
async def change_user_password(user_id: int, new_password: str, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password = hash_password(new_password)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"id": user.id, "number": user.number, "message": "Password updated successfully"}


# CHANGE USER NUMBER


# CHANGE USER NUMBER
@router.patch("/admin/users/{user_id}/number")
async def change_user_number(
    user_id: int,
    new_number: str,
    country_code: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    # Find the user we want to update
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if new number already exists for another user
    full_number = f"{country_code}{new_number}"
    result = await db.execute(select(User).filter(User.number == full_number, User.id != user_id))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail=f"The number {full_number} is already used by another user."
        )

    # Update number
    user.number = full_number
    user.country_code = country_code
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {
        "id": user.id,
        "number": user.number,
        "country_code": user.country_code,
        "message": "Number updated successfully"
    }



# -------------------------
# WITHDRAWAL PIN ROUTES
# -------------------------
from pydantic import BaseModel, constr
from typing import Annotated
from passlib.context import CryptContext

pwd_context_pin = CryptContext(schemes=["argon2"], deprecated="auto")
ARGON2_MAX_LENGTH = 128

def hash_pin(pin: str) -> str:
    return pwd_context_pin.hash(pin[:ARGON2_MAX_LENGTH])

def verify_pin(pin: str, hashed_pin: str) -> bool:
    return pwd_context_pin.verify(pin[:ARGON2_MAX_LENGTH], hashed_pin)

class SetPinRequest(BaseModel):
    pin: Annotated[str, constr(min_length=4, max_length=6)]

class ResetPinRequest(BaseModel):
    user_id: int

# USER: Set own withdrawal PIN
@router.post("/withdrawal-pin/set")
async def set_withdrawal_pin(
    request: SetPinRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    if current_user.withdrawal_pin:
        raise HTTPException(status_code=400, detail="Withdrawal PIN already set. Use change endpoint if needed.")

    current_user.withdrawal_pin = hash_pin(request.pin)
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return {"message": "Withdrawal PIN set successfully"}

# USER: Change existing withdrawal PIN
@router.post("/withdrawal-pin/change")
async def change_withdrawal_pin(
    request: SetPinRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    if not current_user.withdrawal_pin:
        raise HTTPException(status_code=400, detail="No existing PIN found. Please set a PIN first.")

    current_user.withdrawal_pin = hash_pin(request.pin)
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return {"message": "Withdrawal PIN updated successfully"}

# ADMIN: Reset a user's withdrawal PIN
@router.post("/withdrawal-pin/reset")
async def admin_reset_withdrawal_pin(
    request: ResetPinRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(select(User).filter(User.id == request.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.withdrawal_pin = None
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"message": f"Withdrawal PIN for user {user.number} has been reset. User can now set a new PIN."}
