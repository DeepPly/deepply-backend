from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User

router = APIRouter()

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get('/')
def home():
    return {"message": "Welcome to the User API"}

@router.post("/create_user")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    # Check if username or email already exists
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    db_user = User(
        username=user.username,
        email=user.email,
    )
    db_user.set_password(user.password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": "User created", "id": db_user.id}

@router.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user.id, "username": user.username, "email": user.email}

@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [{"id": user.id, "username": user.username, "email": user.email} for user in users]

@router.post("/users/login")
class UserLogin(BaseModel):
    username: str = None
    email: str = None
    password: str

@router.post("/users/login")
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    if not user.username and not user.email:
        raise HTTPException(status_code=400, detail="Username or email required")
    query = db.query(User)
    if user.username:
        db_user = query.filter(User.username == user.username).first()
    else:
        db_user = query.filter(User.email == user.email).first()
    if not db_user or not db_user.verify_password(user.password):
        raise HTTPException(status_code=400, detail="Invalid username/email or password")
    return {"message": "Login successful", "id": db_user.id}