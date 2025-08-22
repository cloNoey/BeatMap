from pathlib import Path
from typing import Optional, Tuple

import soundfile as sf
from app.core.config import settings


def ensure_wav(
    input_path: str,
    target_sr: Optional[int] = None,
    mono: bool = True,
    strict: bool = False,
) -> Tuple[str, int, int]:
    """
    매우 빠른 .wav 보장 함수 (변환 없이 메타만 확인)
    - 입력 파일이 .wav가 아니면 에러
    - 메타데이터만 읽어 sample_rate, duration_ms 계산
    - (옵션) target_sr/mono 요구 조건 검증:
        * strict=True 이면 불일치 시 예외 발생
        * strict=False 이면 경고 수준으로 무시하고 그대로 반환

    Returns:
        (out_path:str, samplerate:int, duration_ms:int)
    """
    in_path = Path(input_path)
    if not in_path.exists():
        raise FileNotFoundError(f"Input audio not found: {in_path}")
    if in_path.suffix.lower() != ".wav":
        raise ValueError(f"Expected .wav input, got: {in_path.suffix}")

    # 메타만 읽기 (빠름)
    info = sf.info(str(in_path))
    sr = int(info.samplerate)
    ch = int(info.channels)
    if sr <= 0:
        raise RuntimeError(f"Invalid samplerate for {in_path}: {sr}")

    duration_ms = int(info.frames / info.samplerate * 1000)
    desired_sr = int(target_sr or settings.TARGET_SR)

    # 검증(옵션)
    sr_ok = (sr == desired_sr)
    ch_ok = (not mono) or (ch == 1)

    if strict:
        if not sr_ok:
            raise ValueError(f"Sample rate mismatch: got {sr}, expected {desired_sr}")
        if not ch_ok:
            raise ValueError(f"Channel count mismatch: got {ch}, expected mono(1)")
    else:
        # 필요하다면 여기서 logger.warning으로 알림만 남길 수 있음
        # logger.warning(f"...")  # 로거 사용 중이면 주석 해제
        pass

    return str(in_path), sr, duration_ms