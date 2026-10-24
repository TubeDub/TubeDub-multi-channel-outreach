"""Безопасная миграция: бэкап + обновление схемы."""
import asyncio
import os
import sys
from pathlib import Path

# allow running as module or script
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.storage.database import init_db, backup_db
from app.config import DATABASE_PATH

async def main():
    db_path = os.getenv("DATABASE_PATH", DATABASE_PATH)
    print(f"[migrate] DB path: {db_path}")
    if os.path.exists(db_path):
        dst = backup_db(db_path)
        print(f"[migrate] Backup created: {dst}")
    else:
        print("[migrate] No existing DB, will create new")
    await init_db(db_path)
    print("[migrate] Migration completed successfully")
    print("[migrate] Existing campaigns/settings/history preserved if present")

if __name__ == "__main__":
    asyncio.run(main())
