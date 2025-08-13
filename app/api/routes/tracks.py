from fastapi import APIRouter, UploadFile, File, HTTPException
import os, shutil, asyncio, subprocess, tempfile
from app.core.config import settings
from app.db.session import SESSION
from app.db.models.track import Track, SourceType
from sqlalchemy import insert, update
from starlette.status import HTTP_201_CREATED
import yt_dlp

router = APIRouter()

def _tracks_dir() -> str:
    dest_dir = os.path.join(settings.STORAGE_DIR, "tracks")
    os.makedirs(dest_dir, exist_ok=True)
    return dest_dir

async def _create_stub_record(*, filename: str, source_type: SourceType, status: str = "pending") -> int:
    async with SESSION() as db:
        stmt = insert(Track).values(
            title=filename,
            source_type=source_type,
            file_path="",
            status=status
        )
        res = await db.execute(stmt)
        await db.commit()
        return res.inserted_primary_key[0]

async def _finalize_record(track_id: int, file_path: str, status: str = "pending") -> None:
    async with SESSION() as db:
        stmt = update(Track).where(Track.id == track_id).values(file_path=file_path, status=status)
        await db.execute(stmt)
        await db.commit()

async def _ffmpeg_convert_to_wav(src_path: str, dst_path: str) -> None:
    def _run():
        cmd = ["ffmpeg", "-y", "-i", src_path, "-acodec", "pcm_s16le", "-ar", "44100", dst_path]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        await asyncio.to_thread(_run)
    except FileNotFoundError:
        raise HTTPException(500, "ffmpeg가 설치되어 있지 않습니다.")
    except subprocess.CalledProcessError:
        raise HTTPException(500, "오디오를 wav로 변환하는 중 오류가 발생했습니다.")

async def _download_first_youtube_audio_to_wav(url: str) -> tuple[str, str]:
    tmp_dir = tempfile.mkdtemp()
    outtmpl = os.path.join(tmp_dir, "%(id)s.%(ext)s")

    # bestaudio 그대로 받아서 ffmpeg로 wav 변환
    ydl_opts = {
        "outtmpl": outtmpl,
        "format": "bestaudio/best",
        "playlist_items": "1",
        "noplaylist": False,
        "prefer_ffmpeg": True,
        "quiet": True,
    }

    def _run():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            entry = info["entries"][0] if info.get("_type") == "playlist" and info.get("entries") else info
            vid_id = entry["id"]
            title = entry.get("title") or vid_id

            # 다운로드된 원본 파일 경로 추적
            for root, _, files in os.walk(tmp_dir):
                for fname in files:
                    if fname.startswith(vid_id):
                        return os.path.join(root, fname), title
            raise HTTPException(500, "YouTube 오디오 다운로드 실패")

    return await asyncio.to_thread(_run)

# ------- endpoint -------
@router.post("/upload", status_code=HTTP_201_CREATED)
async def upload_track(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".mp3", ".wav", ".flac"]:
        raise HTTPException(400, "Unsupported file type")

    original_name = file.filename
    track_id = await _create_stub_record(filename=original_name, source_type=SourceType.upload)

    dest_dir = _tracks_dir()
    final_path = os.path.join(dest_dir, f"{track_id}.wav")

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp_path = tmp.name
        def _save_tmp():
            with open(tmp_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
        await asyncio.to_thread(_save_tmp)

    try:
        await _ffmpeg_convert_to_wav(tmp_path, final_path)
        os.remove(tmp_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise

    await _finalize_record(track_id, final_path)
    return {"id": track_id, "status": "pending"}

@router.post("/upload_yt", status_code=HTTP_201_CREATED)
async def upload_track_youtube(url: str):
    tmp_audio_path, video_title = await _download_first_youtube_audio_to_wav(url)
    track_id = await _create_stub_record(filename=video_title, source_type=SourceType.youtube)

    dest_dir = _tracks_dir()
    final_path = os.path.join(dest_dir, f"{track_id}.wav")

    await _ffmpeg_convert_to_wav(tmp_audio_path, final_path)

    # 원본 삭제
    try:
        os.remove(tmp_audio_path)
        os.rmdir(os.path.dirname(tmp_audio_path))
    except Exception:
        pass

    await _finalize_record(track_id, final_path)
    return {"id": track_id, "status": "pending"}