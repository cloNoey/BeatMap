from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    APP_ENV: str = "dev"

    REDIS_URL: str = "redis://localhost:6379/0"
    RQ_QUEUE: str = "analysis"

    STORAGE_BACKEND: str = "local"
    STORAGE_DIR: str = "./data"

    FFMPEG_BIN: str = "ffmpeg"

    TARGET_SR: int = 22050
    PEAKS_DOWNSAMPLE: int = 4000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
os.makedirs(settings.STORAGE_DIR, exist_ok=True)