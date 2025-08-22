import numpy as np
import librosa
from dataclasses import dataclass

@dataclass
class BeatGrid:
    bpm: float
    beat_times: np.ndarray   # seconds
    onset_times: np.ndarray  # seconds
    confidence: float


def compute_beat_grid(wav_path: str, sr: int) -> BeatGrid:
    # 통일된 hop_length 사용 (librosa 기본값 512과 동일)
    HOP = 512

    y, _ = librosa.load(wav_path, sr=sr, mono=True)
    # NaN/Inf 방지 및 정규화
    if np.allclose(y, 0):
        y = np.zeros_like(y)
    else:
        y = librosa.util.normalize(y)

    # 1) 비트 트래킹
    tempo, beat_frames = librosa.beat.beat_track(
        y=y, sr=sr, hop_length=HOP, units="frames"
    )
    beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=HOP)

    # 2) 온셋 엔벌로프 / 온셋 검출
    onset_env = librosa.onset.onset_strength(
        y=y, sr=sr, hop_length=HOP, aggregate=np.median
    )
    env_t = librosa.times_like(onset_env, sr=sr, hop_length=HOP)

    onset_frames = librosa.onset.onset_detect(
        onset_envelope=onset_env, sr=sr, hop_length=HOP, units="frames"
    )
    onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=HOP)

    # 3) "비트 그리드"에 해당하는 onset_env 샘플 값의 평균으로 간이 confidence 계산
    confidence = 0.0
    if len(beat_times) > 2:
        period = float(np.median(np.diff(beat_times)))
        if period > 0:
            phase = float(beat_times[0])
            t_max = float(env_t[-1])

            if phase <= t_max:
                # phase..t_max까지 period 간격의 그리드 생성
                n = int(np.floor((t_max - phase) / period)) + 1
                grid = phase + np.arange(n, dtype=float) * period  # (n,)

                # 그리드 시간을 onset_env 프레임 인덱스로 매핑 (정수 인덱싱)
                grid_idx = np.searchsorted(env_t, np.clip(grid, 0.0, t_max), side="left")
                # 경계 클립
                grid_idx = np.clip(grid_idx, 0, len(onset_env) - 1)

                denom = float(np.max(onset_env) + 1e-9)
                if grid_idx.size > 0 and denom > 0.0:
                    confidence = float(np.mean(onset_env[grid_idx]) / denom)
                else:
                    confidence = 0.0
            else:
                confidence = 0.0
        else:
            confidence = 0.0

    return BeatGrid(
        bpm=float(tempo),
        beat_times=beat_times,
        onset_times=onset_times,
        confidence=confidence,
    )


def estimate_phase_shift(beat_times: np.ndarray, onset_times: np.ndarray) -> float:
    if len(beat_times) < 2 or len(onset_times) == 0:
        return 0.0
    period = float(np.median(np.diff(beat_times)))
    if period <= 0:
        return 0.0

    shifts = np.linspace(-period, period, 41)
    best_shift, best_score = 0.0, -1.0
    base = float(beat_times[0])

    for s in shifts:
        snapped = np.round((onset_times - (base + s)) / period)
        recon = (base + s) + snapped * period
        score = float(np.mean(np.abs(onset_times - recon) < 0.07))
        if score > best_score:
            best_shift, best_score = float(s), score
    return best_shift


def map_to_8count(beat_times: np.ndarray, phase_shift: float):
    if len(beat_times) == 0:
        return []
    period = float(np.median(np.diff(beat_times))) if len(beat_times) > 1 else 0.5
    base = float(beat_times[0] + phase_shift)

    out = []
    for i, t in enumerate(beat_times):
        idx = int(np.round((float(t) - base) / period)) if period > 0 else i
        count = (idx % 8) + 1
        measure = idx // 8
        out.append((i, int(float(t) * 1000), count, measure))
    return out