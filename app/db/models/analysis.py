from sqlalchemy import BigInteger, Column, Float, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.db.base import Base

class Analysis(Base):
    __tablename__ = "analysis"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    track_id = Column(BigInteger, ForeignKey("track.id", ondelete="CASCADE"), nullable=False)
    bpm = Column(Float)
    beat_confidence = Column(Float)
    beat_phase_shift_ms = Column(Integer, default=0)
    measures = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())