from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from typing_extensions import Annotated
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
import jwt
import os
from database import SessionLocal
from models import User
from jwt.exceptions import InvalidTokenError
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Callable

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_db():
    db = SessionLocal()
    try:    
        yield db
    finally:
        db.close()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(db, username: str):
    user = db.query(User).filter(User.username == username).first()
    print(user)
    if user:
        return user

def auth_user(db, username: str, password: str):
    user = get_user(db, username)
    if not user or not hasattr(user, 'password_hash'):
        return False
    if not verify_password(password, user.password_hash):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_ex = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get('sub')
        if username is None:
            raise credentials_ex
    except InvalidTokenError:
        raise credentials_ex
    db = next(get_db())
    user = get_user(db, username=username)
    if user is None:
        raise credentials_ex
    return user

async def get_current_active_user(token: Annotated[str, Depends(oauth2_scheme)]):
    user = await get_current_user(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

def login_required(func: Callable):
    @wraps(func)
    async def wrapper(*args, user: User = Depends(get_current_active_user), **kwargs):
        return await func(*args, user=user, **kwargs)
    return wrapper