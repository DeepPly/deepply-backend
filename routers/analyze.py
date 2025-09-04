from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from auth_utils import get_current_active_user
from database import SessionLocal
from utils.analyze import analyze_position
from pydantic import BaseModel
from models import Analysis, User

router = APIRouter()

class PositionAnalysisRequest(BaseModel):
    fen: str
    depth: int = 20

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get('/analyze', response_model=dict)
def analyze_pos_route(request: PositionAnalysisRequest, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    check = db.query(Analysis).filter(Analysis.fen == request.fen, Analysis.depth == request.depth).first()
    if check:
        return check

    result = analyze_position(request.fen, request.depth)
    AnalysisRecord = Analysis(
        fen=request.fen, 
        depth=request.depth, 
        evaluation=result.get("evaluation"), 
        top_moves=result.get("top_moves"),
        owner_id=user.id
    )
    db.add(AnalysisRecord)
    db.commit()
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result