import subprocess, os, math
import soundfile as sf
from pydub import AudioSegment
from app.core.config import settings

def ensure_wav(input_path: str, target_sr: int | None = None):
    # Convert any audio to mono WAV + target SR via ffmpeg
    target_sr = target_sr or settings.TARGET_SR
    out_path = os.path.splitext(input_path)[0] + f"_{target_sr}.wav"
    cmd = [settings.FFMPEG_BIN, "-y", "-i", input_path, "-ac", "1", "-ar", str(target_sr), out_path]
    subprocess.run(cmd, check=True, capture_output=True)
    info = sf.info(out_path)
    duration_ms = int(info.frames / info.samplerate * 1000)
    return out_path, info.samplerate, duration_ms