from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Game
from pydantic import BaseModel

router = APIRouter()

class GameUpload(BaseModel):
    pgn: str
    format: str = "Online"
    description: str = ""

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/upload_game")
def upload_game(data: GameUpload, db: Session = Depends(get_db)):
    new_game = Game(
        pgn=data.pgn,
        format=data.format,
        description=data.description,
        user_id=1 
    )
    db.add(new_game)
    db.commit()
    db.refresh(new_game)
    return {"message": "Game uploaded", "id": new_game.id}
