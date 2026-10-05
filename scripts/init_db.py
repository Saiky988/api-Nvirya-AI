import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth.api_keys import ApiKeyService
from app.core.config import settings
from app.db.database import get_db, init_db
from app.db.repositories import UserRepository

async def main():
    print(f"Initializing database at: {settings.sqlite_db_path}")
    await init_db()
    print("Database tables and indexes created successfully.")

    # Create default user and API key if none exists
    async for db in get_db():
        default_user = await UserRepository.get_user_by_id(db, "usr_admin")
        if not default_user:
            default_user = await UserRepository.create_user(
                db=db,
                user_id="usr_admin",
                username="admin",
                email="admin@nvirya.local",
            )
            print(f"Created initial user: {default_user.username} ({default_user.id})")

            plain_key, api_key = await ApiKeyService.create_key_for_user(
                db=db,
                user_id=default_user.id,
                label="Admin Initial Key",
            )
            print("====================================================")
            print(" INITIAL API KEY GENERATED (STORE SECURELY):")
            print(f" {plain_key}")
            print("====================================================")
        else:
            print(f"Initial user '{default_user.username}' already exists.")
        break

if __name__ == "__main__":
    asyncio.run(main())
