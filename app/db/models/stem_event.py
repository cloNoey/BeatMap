from sqlalchemy import BigInteger, Column, Float, Integer, ForeignKey, Enum
from app.db.base import Base

class StemEvent(Base):
    __tablename__ = "stem_event"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    stem_id = Column(BigInteger, ForeignKey("stem.id", ondelete="CASCADE"), nullable=False)
    ts_ms = Column(Integer, nullable=False)
    strength = Column(Float)
    event_type = Column(Enum("onset","accent", name="event_type"), default="onset")
    count_in_8 = Column(Integer)
    measure_index = Column(Integer)
