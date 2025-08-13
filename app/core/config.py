from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    APP_ENV: str = "dev"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    DATABASE_URL: str
    REDIS_URL: str
    RQ_QUEUE: str = "analysis"

    STORAGE_BACKEND: str = "local"
    STORAGE_DIR: str = "./data"

    FFMPEG_BIN: str = "ffmpeg"

    TARGET_SR: int = 22050
    PEAKS_DOWNSAMPLE: int = 4000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
os.makedirs(settings.STORAGE_DIR, exist_ok=True)