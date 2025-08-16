import asyncio
from typing import Optional
from contextvars import ContextVar, Token
from uuid import uuid4
from sqlalchemy import AsyncAdaptedQueuePool
from sqlalchemy.ext.asyncio import (
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)

from app.db.config import DatabaseSettings
settings = DatabaseSettings()
class DatabaseManager:
    def __init__(self):
        # Python 3.11 + SQLAlchemy 2.x 권장: aiomysql 사용
        url = settings.url  # mysql이면 driver 자동 보정
        self.engine = create_async_engine(
            url,
            poolclass=AsyncAdaptedQueuePool,
            pool_recycle=28000,      # RDS wait_timeout 대비
            pool_pre_ping=True,      # 죽은 커넥션 사전 감지
            # 필요시 타임아웃/SSL 등 추가
            # connect_args={"connect_timeout": 5, "ssl": {"ssl": True}},
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
        )


# 세션 컨텍스트(요청/태스크 스코프)
session_context_var: ContextVar[tuple[str | None, str | None]] = ContextVar(
    "session_context", default=(None, None)
)


def reset_session(token: Token) -> None:
    """세션 컨텍스트 초기화"""
    session_context_var.reset(token)


def start_default_session() -> Token:
    """DefaultSessionMiddleware 등에서 최초 1회 호출"""
    return session_context_var.set((uuid4().hex, None))


def start_new_session_if_not_exists() -> Optional[Token]:
    """현재 asyncio task에 세션 스코프가 없으면 생성"""
    _, session_task = session_context_var.get()
    current_task_name = asyncio.current_task().get_name()  # type: ignore
    if session_task != current_task_name:
        return session_context_var.set((uuid4().hex, current_task_name))
    return None


def get_session_id() -> str | None:
    """async_scoped_session scopefunc: 세션 스코프 키 반환"""
    return session_context_var.get()[0]


SESSION = async_scoped_session(
    session_factory=DatabaseManager().session_factory,
    scopefunc=get_session_id,
)