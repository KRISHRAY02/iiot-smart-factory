from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# Demo single-user credential store. Password is hashed at import time so it
# never sits in memory/logs in plaintext form beyond process start.
_DEMO_USERS = {
    settings.demo_username: pwd_context.hash(settings.demo_password),
}


def authenticate_user(username: str, password: str) -> bool:
    hashed = _DEMO_USERS.get(username)
    if not hashed:
        return False
    return pwd_context.verify(password, hashed)


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return username
    except JWTError:
        raise credentials_exception


credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    if not token:
        raise credentials_exception
    return decode_token(token)


def verify_ws_token(token: str) -> str:
    """Validate a JWT passed as a websocket query param."""
    if not token:
        raise credentials_exception
    return decode_token(token)
