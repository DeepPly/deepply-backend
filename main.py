from fastapi import FastAPI, Depends, HTTPException, status
from typing import Annotated
from pydantic import BaseModel
from routers import upload, user
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

app.include_router(upload.router)
app.include_router(user.router)
