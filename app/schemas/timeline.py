from pydantic import BaseModel
from typing import List, Dict

class BeatItem(BaseModel):
    idx: int
    ms: int
    count: int
    measure: int

class EventItem(BaseModel):
    ms: int
    strength: float
    count: int | None = None
    measure: int | None = None

class StemLane(BaseModel):
    events: List[EventItem]

class TimelineOut(BaseModel):
    trackId: int
    bpm: float
    beatGrid: List[BeatItem]
    stems: Dict[str, StemLane]

