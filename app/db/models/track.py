from sqlalchemy import BigInteger, Column, Integer, String, Enum, DateTime, Text
from sqlalchemy.sql import func
from app.db.base import Base
import enum

class SourceType(str, enum.Enum):
    upload = "upload"
    youtube = "youtube"

class Track(Base):
    __tablename__ = "track"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(String(255))
    source_type = Column(Enum(SourceType), nullable=False)
    file_path = Column(String(512))
    sample_rate = Column(Integer)
    duration_ms = Column(Integer)
    status = Column(Enum("pending","processing","done","failed", name="track_status"), default="pending")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())