# from fastapi import APIRouter, Depends, HTTPException
# from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# import random
# import string

# from app.database.database import get_async_db
# from app.models.models import User, Wallet
# from app.core.jwt import hash_password, verify_password, create_access_token, decode_access_token
# from app.schema.schema import UserCreate, UserLogin, Token

# router = APIRouter(prefix="/auth", tags=["Authentication"])
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# # ------------------------
# # Helper: generate referral code
# # ------------------------
# def generate_referral_code(length: int = 6):
#     return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


# # ------------------------
# # REGISTER
# # ------------------------
# @router.post("/register", response_model=Token)
# async def register(user: UserCreate, db: AsyncSession = Depends(get_async_db)):
#     full_number = f"{user.country_code}{user.number}"

#     # Check if user already exists
#     result = await db.execute(select(User).filter(User.number == full_number))
#     db_user = result.scalar_one_or_none()
#     if db_user:
#         raise HTTPException(status_code=400, detail="User already exists")

#     # Generate unique referral code
#     while True:
#         referral_code = generate_referral_code()
#         exists = await db.execute(select(User).filter(User.referral_code == referral_code))
#         if not exists.scalar_one_or_none():
#             break

#     # Validate referred_by if provided
#     referred_by = None
#     if user.referral:
#         result = await db.execute(select(User).filter(User.referral_code == user.referral))
#         ref_user = result.scalar_one_or_none()
#         if ref_user:
#             referred_by = user.referral

#     # Create user
#     new_user = User(
#         number=full_number,
#         country_code=user.country_code,
#         password=hash_password(user.password),
#         referral_code=referral_code,
#         referred_by=referred_by
#     )
#     db.add(new_user)
#     await db.commit()
#     await db.refresh(new_user)

#     # Create wallet with 0 balances
#     wallet = Wallet(user_id=new_user.id, balance=0.0, income=0.0)
#     db.add(wallet)
#     await db.commit()
#     await db.refresh(wallet)

#     # Return JWT
#     access_token = create_access_token({"sub": new_user.number})
#     return {"access_token": access_token, "token_type": "bearer"}


# # ------------------------
# # LOGIN
# # ------------------------

# def normalize_number(number: str):
#     if number.startswith("0"):
#         return "+254" + number[1:]
#     return number

# @router.post("/login", response_model=Token)
# async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_async_db)):
#     full_number = normalize_number(form_data.username)

#     result = await db.execute(select(User).filter(User.number == full_number))
#     user = result.scalar_one_or_none()
#     if not user or not verify_password(form_data.password, user.password):
#         raise HTTPException(status_code=401, detail="Invalid credentials")

#     access_token = create_access_token({"sub": user.number,"user_id": user.id})
#     return {"access_token": access_token, "token_type": "bearer"}



# # ------------------------
# # GET CURRENT USER
# # ------------------------
# async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_async_db)):
#     payload = decode_access_token(token)
#     if payload is None:
#         raise HTTPException(status_code=401, detail="Invalid token")

#     number = payload.get("sub")
#     result = await db.execute(select(User).filter(User.number == number))
#     user = result.scalar_one_or_none()
#     if not user:
#         raise HTTPException(status_code=401, detail="User not found")
#     return user


# @router.get("/me")
# async def read_users_me(current_user: User = Depends(get_current_user)):
#     return {
#         "id": current_user.id,
#         "number": current_user.number,
#         "country_code": current_user.country_code,
#         "referral_code": current_user.referral_code,
#         "referred_by": current_user.referred_by
#     }



from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
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
@router.post("/register", response_model=Token)
async def register(user: UserCreate, db: AsyncSession = Depends(get_async_db)):
    full_number = f"{user.country_code}{user.number}"

    # Check if user already exists
    result = await db.execute(select(User).filter(User.number == full_number))
    db_user = result.scalar_one_or_none()
    if db_user:
        raise HTTPException(status_code=400, detail="User already exists")

    # Generate unique referral code
    while True:
        referral_code = generate_referral_code()
        exists = await db.execute(select(User).filter(User.referral_code == referral_code))
        if not exists.scalar_one_or_none():
            break

    # Validate referred_by if provided
    referred_by = None
    if user.referral:
        result = await db.execute(select(User).filter(User.referral_code == user.referral))
        ref_user = result.scalar_one_or_none()
        if ref_user:
            referred_by = user.referral

    # Check if this is the first user, make admin
    result = await db.execute(select(User))
    is_first_user = not result.scalar_one_or_none()

    # Create user
    new_user = User(
        number=full_number,
        country_code=user.country_code,
        password=hash_password(user.password),
        referral_code=referral_code,
        referred_by=referred_by,
        is_admin=is_first_user,        # first user is admin
        is_suspended=False
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Create wallet with 0 balances
    wallet = Wallet(user_id=new_user.id, balance=0.0, income=0.0)
    db.add(wallet)
    await db.commit()
    await db.refresh(wallet)

    # Return JWT
    access_token = create_access_token({"sub": new_user.number, "user_id": new_user.id})
    return {"access_token": access_token, "token_type": "bearer"}


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
        raise HTTPException(status_code=403, detail="User is suspended")

    access_token = create_access_token({"sub": user.number, "user_id": user.id})
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
@router.patch("/admin/users/{user_id}/number")
async def change_user_number(user_id: int, new_number: str, country_code: str, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    full_number = f"{country_code}{new_number}"
    user.number = full_number
    user.country_code = country_code
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"id": user.id, "number": user.number, "country_code": user.country_code, "message": "Number updated successfully"}
