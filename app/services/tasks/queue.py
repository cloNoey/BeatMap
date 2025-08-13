from rq import Queue
from redis import Redis
from app.core.config import settings

_redis = Redis.from_url(settings.REDIS_URL)
queue = Queue(settings.RQ_QUEUE, connection=_redis)

# Import inside function to avoid worker import cycles

def enqueue_analysis(track_id: int) -> str:
    from app.services.tasks.jobs import analyze_track_job
    job = queue.enqueue(analyze_track_job, track_id, job_timeout=60*30)
    return job.get_id()