# schemas.py
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
