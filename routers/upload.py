from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from auth_utils import get_current_active_user
from database import SessionLocal
from models import Game, User
from pydantic import BaseModel
from utils.pgnvalidate import validate_pgn, game_analysis

router = APIRouter(
    dependencies=[Depends(get_current_active_user)]
)

class GameUpload(BaseModel):
    user_color: bool = 0
    pgn: str
    time_control: str = 'rapid'
    game_type: str = 'otb'
    description: str = ''
    opponent_rating: int | None = None
    result: str = "1/2-1/2"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()    

@router.post("/review")
def upload_game(data: GameUpload, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    is_valid, error_message = validate_pgn(data.pgn)
    

    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message) 
    
    game_analysis_result = game_analysis(data.pgn)
    
    new_game = Game(
        user_id=user.id, 
        user_color=data.user_color,
        pgn=data.pgn,
        time_control=data.time_control,
        game_type=data.game_type,
        description=data.description,
        opponent_rating=data.opponent_rating,
        result=data.result
    )
    db.add(new_game)
    db.commit()
    db.refresh(new_game)
    return {"message": "Game uploaded", "id": new_game.id, 'analysis': game_analysis_result}

@router.get("/games/{game_id}")
def get_game(game_id: int, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return {"game": game}

@router.get("/games")
def list_games(db: Session = Depends(get_db)):
    games = db.query(Game).all()
    return [{"id": game.id, "user_id": game.user_id, "pgn": game.pgn} for game in games]

@router.get("/users/{user_id}/games")
def list_user_games(user_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    if user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view these games")
    games = db.query(Game).filter(Game.user_id == user_id).all()
    return [{"id": game.id, "pgn": game.pgn} for game in games]