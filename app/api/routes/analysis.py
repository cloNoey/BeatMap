from fastapi import APIRouter, HTTPException
from app.db.session import SESSION
from app.db.models.track import Track
from rq import Queue
from redis import Redis
from app.core.config import settings
import asyncio

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
        # if track.status not in ("pending", "failed", "", ""):  # 이미 처리중/완료면 거절
        #     raise HTTPException(409, f"Already {track.status}")

        track.status = "queued"
        await db.commit()
    job = await asyncio.to_thread(
        queue.enqueue,
        analyze_track_job,  # 동기 함수
        track_id,
        job_timeout=60 * 30,
        result_ttl=60 * 60,  # 선택: 결과 보존 1h
        failure_ttl=24 * 60 * 60,  # 선택: 실패 보존 1d
        description=f"analyze track {track_id}",
    )
    return {"job_id": job.id, "status": "queued"}