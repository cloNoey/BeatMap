import numpy as np, soundfile as sf
from app.core.config import settings

# Return small binary (int16) preview peaks for fast waveform rendering

def compute_peak_preview(wav_path: str) -> bytes:
    data, sr = sf.read(wav_path, dtype='float32', always_2d=False)
    if data.ndim > 1:
        data = data.mean(axis=1)
    n = settings.PEAKS_DOWNSAMPLE
    step = max(1, len(data)//n)
    # compute peak (max abs) in each window
    peaks = [float(np.max(np.abs(data[i:i+step]))) for i in range(0, len(data), step)]
    peaks = np.array(peaks[:n])
    # scale to int16
    peaks_i16 = (peaks * 32767.0).astype('<i2')
    return peaks_i16.tobytes()