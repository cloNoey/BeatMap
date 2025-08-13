from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.track import Track, SourceType
from app.core.config import settings
import os, shutil

router = APIRouter()

@router.post("/upload")
def upload_track(file: UploadFile = File(...), db: Session = Depends(get_db)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".mp3", ".wav", ".flac"]:
        raise HTTPException(400, "Unsupported file type")
    dest_dir = os.path.join(settings.STORAGE_DIR, "tracks")
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, file.filename)
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    t = Track(title=file.filename, source_type=SourceType.upload, file_path=dest_path, status="pending")
    db.add(t); db.commit(); db.refresh(t)
    return {"id": t.id, "status": t.status}
