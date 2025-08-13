from fastapi import APIRouter, HTTPException
from app.db.session import SESSION
from app.services.audio.timeline import build_timeline

router = APIRouter()

@router.get("/{track_id}/timeline")
async def get_timeline(track_id: int):
    async with SESSION() as db:
        data = await build_timeline(db, track_id)
    if data is None:
        raise HTTPException(404, "Timeline not ready")
    return data