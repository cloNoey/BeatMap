from fastapi import APIRouter, HTTPException
from app.db.session import SESSION
from app.db.models.track import Track
from rq import Queue
from redis import Redis
from app.core.config import settings
from app.services.tasks.jobs import analyze_track_job

router = APIRouter()
redis_conn = Redis.from_url(settings.REDIS_URL)
queue = Queue(settings.RQ_QUEUE, connection=redis_conn)

@router.post("/{track_id}/start")
async def start_analysis(track_id: int):
    async with SESSION() as db:
        track = await db.get(Track, track_id)
        if not track:
            raise HTTPException(404, "Track not found")
        status = await db.get(Track, status)
        if status != "pending":
            raise HTTPException(409, "Already analyzed or in progress")

    job = queue.enqueue(analyze_track_job, track_id, job_timeout=60*30)
    return {"job_id": job.id}