from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.timeline import TimelineOut, BeatItem, StemLane, EventItem
from app.services.audio.timeline import build_timeline

router = APIRouter()

@router.get("/{track_id}/timeline", response_model=TimelineOut)
def get_timeline(track_id: int, db: Session = Depends(get_db)):
    data = build_timeline(db, track_id)
    if data is None:
        raise HTTPException(404, "Timeline not ready")
    return data
