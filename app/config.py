import os
from multiprocessing import cpu_count
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Torrent Title Parser"
    API_KEY: Optional[str] = None # Set to a secret string to enable auth
    CORS_ORIGINS: List[str] = ["*"] # e.g., ["http://localhost:8000", "http://127.0.0.1:8000"]
    
    # LLM Settings
    LLM_ENABLED: bool = True
    LLM_MODEL_PATH: str = "/models/unsloth-qwen3-0.6b.gguf"
    N_CTX: int = 4096
    N_THREADS: int = int(os.environ.get("OMP_NUM_THREADS", cpu_count()))
    N_BATCH: int = 512
    USE_MMAP: bool = True
    N_GPU_LAYERS: int = 0 # CPU only

    # Database Settings
    DATABASE_URL: str = "sqlite+aiosqlite:///data/app.db"

    # Logging Settings
    LOG_FILE_PATH: str = "logs/app.jsonl"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
