import numpy as np
import librosa
from dataclasses import dataclass

@dataclass
class BeatGrid:
    bpm: float
    beat_times: np.ndarray   # seconds
    onset_times: np.ndarray  # seconds
    confidence: float


def compute_beat_grid(wav_path: str, sr: int):
    y, _ = librosa.load(wav_path, sr=sr, mono=True)
    y = librosa.util.normalize(y)

    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, units='frames')
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    onset_env = librosa.onset.onset_strength(y=y, sr=sr, aggregate=np.median)
    onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)

    # crude confidence: correlation between onset envelope and beat positions
    if len(beat_times) > 2:
        period = np.median(np.diff(beat_times))
        phase = beat_times[0]
        grid = phase + np.arange(int(len(y)/sr/period)+1) * period
        env_t = librosa.times_like(onset_env, sr=sr)
        grid_mask = np.isin(np.searchsorted(env_t, np.clip(grid, 0, env_t[-1])), np.arange(len(onset_env)))
        confidence = float(np.mean(onset_env[grid_mask]) / (np.max(onset_env)+1e-9))
    else:
        confidence = 0.0

    return BeatGrid(bpm=float(tempo), beat_times=beat_times, onset_times=onset_times, confidence=confidence)


def estimate_phase_shift(beat_times: np.ndarray, onset_times: np.ndarray) -> float:
    if len(beat_times) < 2 or len(onset_times) == 0:
        return 0.0
    period = np.median(np.diff(beat_times))
    shifts = np.linspace(-period, period, 41)
    best_shift, best_score = 0.0, -1.0
    for s in shifts:
        snapped = np.round((onset_times - (beat_times[0] + s)) / period)
        recon = (beat_times[0] + s) + snapped * period
        score = np.mean(np.abs(onset_times - recon) < 0.07)
        if score > best_score:
            best_shift, best_score = s, score
    return float(best_shift)


def map_to_8count(beat_times: np.ndarray, phase_shift: float):
    period = np.median(np.diff(beat_times))
    out = []
    for i, t in enumerate(beat_times):
        idx = int(np.round((t - (beat_times[0] + phase_shift)) / period))
        count = (idx % 8) + 1
        measure = idx // 8
        out.append((i, int(t*1000), count, measure))
    return out