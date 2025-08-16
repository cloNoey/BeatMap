from app.db.session import SESSION
from app.core.logging import logger
from app.services.audio.io import ensure_wav
from app.services.audio.analyze import compute_beat_grid, estimate_phase_shift, map_to_8count
from app.services.audio.demucs import separate_stems
from app.services.audio.events import extract_events_and_map
from app.services.audio.peaks import compute_peak_preview
from app.db.models.track import Track
from app.db.models.analysis import Analysis
from app.db.models.stem import Stem


async def analyze_track_job(track_id: int):
    async with SESSION() as db:
        try:
            t = await db.get(Track, track_id)
            if not t:
                logger.error(f"Track {track_id} not found")
                return
            t.status = "processing"; db.commit()

            wav_path, sr, duration_ms = await ensure_wav(t.file_path)
            t.sample_rate = sr; t.duration_ms = duration_ms; db.commit()

            beat = compute_beat_grid(wav_path, sr)
            onset_times = beat.onset_times
            phase = estimate_phase_shift(beat.beat_times, onset_times)
            counts = map_to_8count(beat.beat_times, phase)

            analysis = Analysis(track_id=t.id, bpm=beat.bpm, beat_confidence=beat.confidence,
                                beat_phase_shift_ms=int(phase*1000), measures=max(c[3] for c in counts)+1)
            db.add(analysis); db.commit(); db.refresh(analysis)

            # Stems
            stems = separate_stems(wav_path)
            stem_rows = {}
            for name, path in stems.items():
                preview_bytes = compute_peak_preview(path)
                srow = Stem(track_id=t.id, stem_type=name, file_path=path, peak_preview=preview_bytes)
                db.add(srow); db.commit(); db.refresh(srow)
                stem_rows[name] = srow

            # Events per stem (mapped onto 8-count in DB)
            extract_events_and_map(db, analysis, counts, stems, stem_rows, sr)

            t.status = "done"; db.commit()
            logger.info(f"Track {t.id} analysis done")
        except Exception as e:
            logger.exception(e)
            if t:
                t.status = "failed"; db.commit()
        finally:
            db.close()