"""Utility helpers for password hashing and JWT tokens."""
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Return a bcrypt hash of ``password``."""
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    """Verify that ``plain`` matches the ``hashed`` password."""
    return pwd_context.verify(plain, hashed)

def create_access_token(subject: str, expires_delta: int | None = None) -> str:
    """Generate a JWT token for ``subject``."""
    expire = datetime.utcnow() + timedelta(
        minutes=expires_delta or ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
