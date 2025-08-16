import asyncio
import os
from contextlib import suppress
from pathlib import Path
import soundfile as sf
from anyio import to_thread
from typing import Optional
from app.core.config import settings

async def ensure_wav(input_path: str, target_sr: Optional[int] = None):
    """
    - ffmpeg 실행은 asyncio 서브프로세스로 비동기 처리
    - soundfile.info는 스레드풀로 offload
    - 실패 시 명확한 예외 메시지 포함
    """
    target_sr = target_sr or settings.TARGET_SR
    in_path = Path(input_path)
    if not in_path.exists():
        raise FileNotFoundError(f"Input audio not found: {in_path}")

    out_path = in_path.with_suffix("")  # drop ext
    out_path = Path(f"{out_path}_{target_sr}.wav")

    # ffmpeg 비동기 실행
    proc = await asyncio.create_subprocess_exec(
        settings.FFMPEG_BIN, "-y",
        "-i", str(in_path),
        "-ac", "1",
        "-ar", str(target_sr),
        str(out_path),
        stdout=asyncio.subprocess.DEVNULL,   # 필요 시 PIPE로 바꿔서 로그 수집
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        # 실패 시 생성된 불완전 파일 정리
        with suppress(Exception):
            out_path.unlink(missing_ok=True)
        err = (stderr.decode("utf-8", errors="ignore") or "").strip()
        raise RuntimeError(f"ffmpeg failed (code={proc.returncode}): {err[:500]}")

    # soundfile.info는 동기 호출이므로 스레드풀로
    info = await to_thread.run_sync(sf.info, str(out_path))
    duration_ms = int(info.frames / info.samplerate * 1000)

    return str(out_path), int(info.samplerate), duration_ms