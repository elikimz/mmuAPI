from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt

# secret key (in production, keep in .env)
SECRET_KEY = "supersecretkey123"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Password hashing
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
ARGON2_MAX_LENGTH = 128  # argon2 max length in characters

def hash_password(password: str):
    # truncate to 128 characters safely
    truncated = password[:ARGON2_MAX_LENGTH]
    return pwd_context.hash(truncated)

def verify_password(plain_password, hashed_password):
    truncated = plain_password[:ARGON2_MAX_LENGTH]
    return pwd_context.verify(truncated, hashed_password)

# JWT Token
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
