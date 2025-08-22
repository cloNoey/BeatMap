import subprocess, os, shutil
from app.core.config import settings

STEMS = ["drums","bass","vocals","other"]

def _pick_device() -> str:
    # 환경에 맞게 하드코딩하거나, settings로 관리해도 됨
    # CUDA 사용 가능 서버: "cuda", Apple Silicon: "mps", 그 외: "cpu"
    return getattr(settings, "DEMUCS_DEVICE", "mps")

def _pick_model() -> str:
    # 속도 우선이면 mdx_q, 품질 우선이면 htdemucs_ft 등으로 스위치
    return getattr(settings, "DEMUCS_MODEL", "mdx_q")

def separate_stems(wav_path: str) -> dict:
    out_dir = os.path.splitext(wav_path)[0] + "_stems"
    os.makedirs(out_dir, exist_ok=True)

    device = _pick_device()          # "cuda" | "mps" | "cpu"
    model  = _pick_model()           # "mdx_q" | "htdemucs_ft" | ...

    # 속도 최적화 옵션
    segment = str(getattr(settings, "DEMUCS_SEGMENT", 6))     # seconds
    overlap = str(getattr(settings, "DEMUCS_OVERLAP", 0.10))  # 0~0.25
    shifts  = str(getattr(settings, "DEMUCS_SHIFTS", 1))      # >=1
    jobs    = str(getattr(settings, "DEMUCS_JOBS", 2))        # 병렬 작업 수

    # 예: demucs -n mdx_q -d cuda --segment 6 --overlap 0.1 --shifts 1 -j 2 -o out_dir wav_path
    cmd = [
        "demucs",
        "-n", model,
        "-d", device,
        "--segment", segment,
        "--overlap", overlap,
        "--shifts", shifts,
        "-j", jobs,
        "-o", out_dir,
        wav_path,
    ]
    # 모델 다운로드/로그를 보기 원하면 check=True 그대로 두고, 오래 걸리면 timeout 지정 가능
    subprocess.run(cmd, check=True)

    # Demucs는 모델명 하위 폴더를 만듭니다.
    # 가장 최근 수정 폴더(또는 첫 폴더)를 선택
    subdirs = [p for p in os.listdir(out_dir) if os.path.isdir(os.path.join(out_dir, p))]
    if not subdirs:
        return {}
    # 최신 결과 폴더 선택(동시에 여러 파일을 돌릴 때 안전)
    model_dir = max((os.path.join(out_dir, p) for p in subdirs), key=lambda p: os.path.getmtime(p))

    stem_files = {}
    for s in STEMS:
        # 파일명 끝이 *_{stem}.wav 형태
        cands = [f for f in os.listdir(model_dir) if f.endswith(f"{s}.wav")]
        if cands:
            stem_files[s] = os.path.join(model_dir, cands[0])
    return stem_files