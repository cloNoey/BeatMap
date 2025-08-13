import numpy as np, librosa
from sqlalchemy.orm import Session
from app.db.models.stem_event import StemEvent


def _extract_onsets(wav_path: str, sr: int):
    y, _ = librosa.load(wav_path, sr=sr, mono=True)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, aggregate=np.median)
    peaks = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr)
    times = librosa.frames_to_time(peaks, sr=sr)
    strength = onset_env[peaks] if len(peaks) else np.array([])
    return times, strength


def extract_events_and_map(db: Session, analysis, beat_counts, stems_paths: dict, stem_rows: dict, sr: int):
    # beat_counts: list[(idx, ms, count, measure)] from map_to_8count
    beat_times = np.array([ms for _,ms,_,_ in beat_counts]) / 1000.0
    for name, path in stems_paths.items():
        times, strength = _extract_onsets(path, sr)
        if len(times) == 0:
            continue
        for t, s in zip(times, strength):
            # snap to nearest beat
            idx = int(np.argmin(np.abs(beat_times - t)))
            _, ms, count, measure = beat_counts[idx]
            db.add(StemEvent(stem_id=stem_rows[name].id, ts_ms=ms, strength=float(s), count_in_8=count, measure_index=measure))
        db.commit()