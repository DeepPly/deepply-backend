from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import SessionLocal
from auth_utils import auth_user, create_access_token, get_password_hash, get_current_active_user
from models import User

router = APIRouter()

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserInDB(BaseModel):
    id: int
    username: str
    email: str
    disabled: bool

class RegisterResponse(BaseModel):
    user: UserInDB
    access_token: str
    token_type: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get('/')
def home():
    return {"message": "Welcome to the User API"}

@router.post("/create_user", response_model=UserInDB, status_code=201)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    # Check if username or email already exists
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user.password)
    new_user = User(
        username=user.username,
        email=user.email,
        disabled=False,
        password_hash=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    access_token = create_access_token(data={"sub": user.username})
    return {
        "user": UserInDB(
            id=new_user.id,
            username=new_user.username,
            email=new_user.email,
            disabled=new_user.disabled
        ),
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user.id, "username": user.username, "email": user.email}

@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    users[0].password_hash
    return [{"id": user.id, "username": user.username, "email": user.email, 'pw': user.password} for user in users]

class Token(BaseModel):
    access_token: str
    token_type: str

@router.get("/protected", status_code=200)
def protected(user: User = Depends(get_current_active_user)):
    return {"message": f"Hello, {user.username}. This is a protected route."}

@router.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = auth_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}