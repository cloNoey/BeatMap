from sqlalchemy import BigInteger, Column, Enum, ForeignKey, String, LargeBinary
from app.db.base import Base

class Stem(Base):
    __tablename__ = "stem"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    track_id = Column(BigInteger, ForeignKey("track.id", ondelete="CASCADE"), nullable=False)
    stem_type = Column(Enum("drums","bass","vocals","other", name="stem_type"), nullable=False)
    file_path = Column(String(512))
    peak_preview = Column(LargeBinary)