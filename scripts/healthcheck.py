import asyncio
import sys
from pathlib import Path
import httpx

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.providers.registry import provider_registry

async def check():
    print(f"Checking Nvirya AI components...")
    
    # 1. Database check
    db_file = settings.sqlite_db_path
    if db_file.exists():
        print(f"[OK] SQLite database found at {db_file}")
    else:
        print(f"[WARN] SQLite database file not found yet. Run init_db.py")

    # 2. Storage directories
    if settings.ARTIFACTS_DIR.exists() and settings.TEMP_DIR.exists():
        print(f"[OK] Storage directories verified.")
    else:
        print(f"[ERROR] Storage directories missing.")

    # 3. xKiro provider check
    provider = provider_registry.get_default_provider()
    try:
        models = await provider.list_models()
        print(f"[OK] Upstream xKiro connection verified ({len(models)} models available).")
    except Exception as e:
        print(f"[WARN] Upstream xKiro verification failed: {e}")

    print("Health check complete.")

if __name__ == "__main__":
    asyncio.run(check())
