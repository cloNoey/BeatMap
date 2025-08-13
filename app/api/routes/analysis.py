from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.tasks.queue import enqueue_analysis

router = APIRouter()

@router.post("/{track_id}/start")
def start_analysis(track_id: int, db: Session = Depends(get_db)):
    job_id = enqueue_analysis(track_id)
    return {"job_id": job_id}
