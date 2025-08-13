from sqlalchemy.orm import Session
from app.db.models.track import Track
from app.db.models.analysis import Analysis
from app.db.models.stem import Stem
from app.db.models.stem_event import StemEvent
from app.schemas.timeline import TimelineOut, BeatItem, StemLane, EventItem


def build_timeline(db: Session, track_id: int):
    t = db.get(Track, track_id)
    if not t or t.status != "done":
        return None
    a = db.query(Analysis).filter_by(track_id=track_id).order_by(Analysis.id.desc()).first()
    if not a:
        return None

    # beat grid reconstructed from DB (we didn't persist per-beat rows to simplify MVP)
    # For MVP timeline, we rebuild a simple grid using bpm + phase assuming constant tempo.
    # (Optional: persist detailed beat_grid in DB for perfect recall.)

    # Pull events
    stems = db.query(Stem).filter_by(track_id=track_id).all()
    lanes = {}
    for s in stems:
        events = db.query(StemEvent).filter_by(stem_id=s.id).all()
        lanes[s.stem_type] = StemLane(events=[EventItem(ms=e.ts_ms, strength=e.strength, count=e.count_in_8, measure=e.measure_index) for e in events])

    # lightweight beat grid: infer from events' ms if needed - here we emit empty grid for MVP front to render from events
    beat_grid = [BeatItem(idx=i, ms=e.ms, count=e.count, measure=e.measure) 
                 for lane in lanes.values() for i, e in enumerate(lane.events)]
    # Deduplicate & sort
    seen = {}
    for b in beat_grid:
        seen[(b.ms, b.count, b.measure)] = b
    beat_grid = sorted(seen.values(), key=lambda x: x.ms)

    return TimelineOut(trackId=track_id, bpm=a.bpm or 0.0, beatGrid=beat_grid, stems=lanes)