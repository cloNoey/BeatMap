# backend/worker/worker.py
from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
from typing import List

from redis import Redis
from rq import Worker, Queue
from rq.logutils import setup_loghandlers

# ────────────────────────────────────────────────────────────────────────────
# 프로젝트 루트 경로 추가 (app.* 임포트 보장)
# (이 파일이 backend/worker/worker.py 라면, 루트는 ../../)
# ────────────────────────────────────────────────────────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# settings: REDIS_URL, RQ_QUEUE 등 사용
from app.core.config import settings  # noqa: E402

# ────────────────────────────────────────────────────────────────────────────
# Graceful shutdown (SIGINT/SIGTERM) 지원
# ────────────────────────────────────────────────────────────────────────────
_SHOULD_STOP = False


def _signal_handler(signum, frame):
    global _SHOULD_STOP
    logging.warning("Received signal %s. Will stop after current job.", signum)
    _SHOULD_STOP = True


def _install_signal_handlers():
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)


# ────────────────────────────────────────────────────────────────────────────
# 메인
# ────────────────────────────────────────────────────────────────────────────
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="RQ Worker (latest API)")
    p.add_argument(
        "--queues",
        default=settings.RQ_QUEUE,
        help="Comma-separated queue names (default: settings.RQ_QUEUE)",
    )
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Log verbosity",
    )
    p.add_argument(
        "--burst",
        action="store_true",
        help="Burst mode: exit when queues are empty",
    )
    return p.parse_args()


def main():
    args = parse_args()

    # 로깅 설정
    setup_loghandlers(level=args.log_level)
    logging.getLogger().setLevel(args.log_level)
    logging.info("Starting worker (RQ latest)")

    # Redis 연결
    redis_url = settings.REDIS_URL
    if not redis_url:
        logging.error("REDIS_URL is empty. Check environment.")
        sys.exit(1)

    redis_conn = Redis.from_url(redis_url)

    # 큐 목록
    qnames: List[str] = [q.strip() for q in str(args.queues).split(",") if q.strip()]
    if not qnames:
        logging.error("No queues specified")
        sys.exit(1)

    queues = [Queue(name, connection=redis_conn) for name in qnames]

    # 워커 이름(선택)
    worker_name = os.environ.get("WORKER_NAME")
    if worker_name:
        logging.info("Worker name: %s", worker_name)

    # 신호 처리기
    _install_signal_handlers()

    # 워커 시작 (최신 RQ: Connection 컨텍스트 불필요)
    worker = Worker(queues, connection=redis_conn, name=worker_name)
    logging.info(
        "Worker started. queues=%s, burst=%s, redis=%s",
        qnames, args.burst, redis_url
    )

    # with_scheduler=True 는 rq-scheduler 사용할 때만
    worker.work(with_scheduler=False, burst=args.burst)

    if _SHOULD_STOP:
        logging.info("Worker stopped by signal.")
    else:
        logging.info("Worker exited.")


if __name__ == "__main__":
    main()