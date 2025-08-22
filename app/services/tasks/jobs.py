from __future__ import annotations

import time
import logging
from typing import Dict

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.logging import logger
from app.db.config import DatabaseSettings

# 동기 엔진/세션 (워커 전용, 반드시 pymysql)
_settings = DatabaseSettings()
_sync_url = _settings.url
if _sync_url.startswith("mysql+aiomysql://"):
    _sync_url = _sync_url.replace("mysql+aiomysql://", "mysql+pymysql://", 1)
if _sync_url.startswith("mysql://"):
    _sync_url = _sync_url.replace("mysql://", "mysql+pymysql://", 1)

_engine = create_engine(_sync_url, pool_pre_ping=True, pool_recycle=28000)
_Session = sessionmaker(bind=_engine, autoflush=False, autocommit=False)

# ── 동기 분석 파이프라인 함수들 ──────────────────────────────────────
from app.services.audio.io import ensure_wav            # 동기
from app.services.audio.analyze import (                # 동기
    compute_beat_grid,
    estimate_phase_shift,
    map_to_8count,
)
from app.services.audio.demucs import separate_stems    # 동기
from app.services.audio.events import extract_events_and_map  # 동기
from app.services.audio.peaks import compute_peak_preview      # 동기

# ── ORM 모델 ──────────────────────────────────────────────────────
from app.db.models.track import Track
from app.db.models.analysis import Analysis
from app.db.models.stem import Stem


def analyze_track_job(track_id: int) -> None:
    """
    RQ 워커에서 실행되는 '동기' 잡 함수.
    각 단계 전/후로 상세 로그와 경과 시간을 남긴다.
    """
    db = _Session()
    t: Track | None = None
    t0 = time.time()

    def dt() -> str:
        return f"{time.time() - t0:.2f}s"

    try:
        logger.info(f"[jobs] track={track_id} START")

        # 0) 대상 트랙 로드
        s = time.time()
        t = db.get(Track, track_id)
        logger.info(f"[jobs] loaded track (exists={bool(t)}) dt={time.time()-s:.2f}s total={dt()}")
        if not t:
            logger.error(f"[jobs] Track {track_id} not found — ABORT total={dt()}")
            return

        # 1) 상태 전이: queued -> processing
        s = time.time()
        t.status = "processing"
        db.commit()
        logger.info(f"[jobs] status=processing COMMIT ok dt={time.time()-s:.2f}s total={dt()}")

        # 2) 입력 보장 (WAV 생성/샘플레이트/길이 저장)
        s = time.time()
        logger.info(f"[jobs] ensure_wav START src='{t.file_path}'")
        wav_path, sr, duration_ms = ensure_wav(t.file_path)
        logger.info(
            f"[jobs] ensure_wav DONE out='{wav_path}' sr={sr} dur={duration_ms}ms "
            f"dt={time.time()-s:.2f}s total={dt()}"
        )

        s = time.time()
        t.sample_rate = sr
        t.duration_ms = duration_ms
        db.commit()
        logger.info(f"[jobs] sample_rate/duration COMMIT ok dt={time.time()-s:.2f}s total={dt()}")

        # (선택) 커밋 값 즉시 재확인 (다른 세션 가시성 이슈 추적용)
        row = db.execute(
            text("SELECT sample_rate, duration_ms FROM track WHERE id=:id"),
            {"id": t.id},
        ).fetchone()
        logger.info(f"[jobs] readback sr={getattr(row,'sample_rate',None)} dur={getattr(row,'duration_ms',None)} total={dt()}")

        # 3) 비트/온셋/위상/8카운트 분석
        s = time.time()
        logger.info(f"[jobs] compute_beat_grid START")
        beat = compute_beat_grid(wav_path, sr)
        logger.info(
            f"[jobs] compute_beat_grid DONE bpm={beat.bpm:.2f} "
            f"beats={len(beat.beat_times)} conf={beat.confidence:.3f} "
            f"dt={time.time()-s:.2f}s total={dt()}"
        )

        s = time.time()
        phase = estimate_phase_shift(beat.beat_times, beat.onset_times)
        counts = map_to_8count(beat.beat_times, phase)
        measures = (max(c[3] for c in counts) + 1) if counts else 0
        logger.info(
            f"[jobs] phase/counts DONE phase={phase:.4f}s counts={len(counts)} measures={measures} "
            f"dt={time.time()-s:.2f}s total={dt()}"
        )

        # 4) Analysis 저장
        s = time.time()
        analysis = Analysis(
            track_id=t.id,
            bpm=beat.bpm,
            beat_confidence=beat.confidence,
            beat_phase_shift_ms=int(phase * 1000),
            measures=measures,
        )
        db.add(analysis)
        db.flush()   # PK 필요시 확보
        db.commit()
        logger.info(f"[jobs] analysis INSERT COMMIT ok id={analysis.id} dt={time.time()-s:.2f}s total={dt()}")

        # 5) Stem 분리 및 저장
        s = time.time()
        logger.info(f"[jobs] separate_stems START")
        stems: Dict[str, str] = separate_stems(wav_path)  # {"vocals": path, ...}
        logger.info(f"[jobs] separate_stems DONE stems={list(stems.keys())} dt={time.time()-s:.2f}s total={dt()}")

        stem_rows: dict[str, Stem] = {}
        for name, path in stems.items():
            s_each = time.time()
            preview_bytes = compute_peak_preview(path)
            srow = Stem(track_id=t.id, stem_type=name, file_path=path, peak_preview=preview_bytes)
            db.add(srow)
            db.flush()
            db.commit()
            stem_rows[name] = srow
            logger.info(
                f"[jobs] stem saved type={name} id={srow.id} "
                f"dt={time.time()-s_each:.2f}s total={dt()}"
            )

        # 6) Stem 이벤트 추출/8카운트 맵핑
        s = time.time()
        logger.info(f"[jobs] extract_events_and_map START")
        extract_events_and_map(db, analysis, counts, stems, stem_rows, sr)
        logger.info(f"[jobs] extract_events_and_map DONE dt={time.time()-s:.2f}s total={dt()}")

        # 7) 완료
        s = time.time()
        t.status = "done"
        db.commit()
        logger.info(f"[jobs] status=done COMMIT ok dt={time.time()-s:.2f}s TOTAL={dt()}")
        logger.info(f"[jobs] track={t.id} COMPLETE total={dt()}")

    except Exception as e:
        logger.exception(f"[jobs] analyze_track_job FAILED: {e} total={dt()}")
        try:
            if t is not None:
                t.status = "failed"
                db.commit()
                logger.info(f"[jobs] status=failed COMMIT ok total={dt()}")
        except Exception:
            logger.exception("[jobs] failed to mark track as failed")
        raise
    finally:
        db.close()