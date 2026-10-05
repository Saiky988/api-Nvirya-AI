import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings:
    BASE_DIR: Path = BASE_DIR
    APP_NAME: str = os.getenv("APP_NAME", "Nvirya AI")
    APP_ENV: str = os.getenv("APP_ENV", "production")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

    API_PREFIX: str = os.getenv("API_PREFIX", "/v1")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "nvirya-secret-change-in-production")

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./storage/nvirya.db")
    
    # Path resolution for SQLite file
    @property
    def sqlite_db_path(self) -> Path:
        if self.DATABASE_URL.startswith("sqlite:///"):
            clean = self.DATABASE_URL.replace("sqlite:///", "")
            if clean.startswith("./"):
                return BASE_DIR / clean[2:]
            return Path(clean)
        return BASE_DIR / "storage" / "nvirya.db"

    # Upstream Provider Configuration
    XKIRO_BASE_URL: str = os.getenv("XKIRO_BASE_URL", "https://api.xkiro.com/v1").rstrip("/")
    XKIRO_API_KEY: str = os.getenv("XKIRO_API_KEY") or os.getenv("XKIRO_API") or ""

    # Models
    CODE_MODEL: str = os.getenv("CODE_MODEL", "qwen/qwen3.8-max:free")
    CODE_FALLBACK_MODEL: str = os.getenv("CODE_FALLBACK_MODEL", "mistralai/codestral-2508")
    ANALYSIS_MODEL: str = os.getenv("ANALYSIS_MODEL", "qwen/qwen3.8-omni-flash:free")
    FAST_MODEL: str = os.getenv("FAST_MODEL", "qwen/qwen3.7-flash:free")

    # Rate Limit & Daily Quota
    DAILY_TASK_LIMIT: int = int(os.getenv("DAILY_TASK_LIMIT", "30"))
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "1"))

    # Agent Budgets
    MAX_AGENT_STEPS: int = int(os.getenv("MAX_AGENT_STEPS", "8"))
    MAX_TOOL_CALLS_PER_TASK: int = int(os.getenv("MAX_TOOL_CALLS_PER_TASK", "8"))
    MAX_SEARCH_CALLS: int = int(os.getenv("MAX_SEARCH_CALLS", "5"))
    MAX_FETCH_CALLS: int = int(os.getenv("MAX_FETCH_CALLS", "5"))
    MAX_ARTIFACTS: int = int(os.getenv("MAX_ARTIFACTS", "5"))
    MAX_TASK_SECONDS: int = int(os.getenv("MAX_TASK_SECONDS", "120"))

    # Search
    SEARXNG_URL: str = os.getenv("SEARXNG_URL", "").rstrip("/")

    # Security & Storage Limits
    MAX_REQUEST_BODY_MB: int = int(os.getenv("MAX_REQUEST_BODY_MB", "10"))
    MAX_ARTIFACT_MB: int = int(os.getenv("MAX_ARTIFACT_MB", "10"))

    # Storage paths
    STORAGE_DIR: Path = BASE_DIR / "storage"
    ARTIFACTS_DIR: Path = BASE_DIR / "storage" / "artifacts"
    TEMP_DIR: Path = BASE_DIR / "storage" / "temp"

    def ensure_directories(self) -> None:
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        self.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        self.TEMP_DIR.mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.ensure_directories()
