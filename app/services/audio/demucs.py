import subprocess, os
from app.core.config import settings

STEMS = ["drums","bass","vocals","other"]

# Uses demucs CLI to produce 4 stems next to the wav.
# Returns dict {stem_name: path}

def separate_stems(wav_path: str) -> dict:
    out_dir = os.path.splitext(wav_path)[0] + "_stems"
    os.makedirs(out_dir, exist_ok=True)
    cmd = ["demucs", wav_path, "-o", out_dir]
    subprocess.run(cmd, check=True)
    # Demucs creates subfolder per model; find first set
    model_dir = next((os.path.join(out_dir, p) for p in os.listdir(out_dir) if os.path.isdir(os.path.join(out_dir,p))), out_dir)
    stem_files = {}
    for s in STEMS:
        # best-effort match
        cand = [f for f in os.listdir(model_dir) if f.endswith(f"{s}.wav")] 
        if cand:
            stem_files[s] = os.path.join(model_dir, cand[0])
    return stem_files