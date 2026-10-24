import aiosqlite
from datetime import datetime
from pathlib import Path

class AccountManager:
    """Позволяет несколько аккаунтов на один канал: хранит account_id per platform"""
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS channel_accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_id INTEGER NOT NULL,
                    platform TEXT NOT NULL,
                    account_label TEXT NOT NULL, -- например @username или телефон
                    session_path TEXT,
                    status TEXT DEFAULT 'not_connected',
                    first_seen_at TEXT,
                    created_at TEXT,
                    UNIQUE(owner_id, platform, account_label)
                )
            """)
            await db.commit()

    async def add_account(self, owner_id: int, platform: str, label: str, session_path: str = ""):
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO channel_accounts (owner_id, platform, account_label, session_path, status, first_seen_at, created_at) VALUES (?, ?, ?, ?, 'connected', ?, ?)",
                (owner_id, platform, label, session_path, now, now)
            )
            await db.commit()
            # также обновить лимитер first_seen
            from app.services.account_rate_limiter import AccountRateLimiter
            lim = AccountRateLimiter(self.db_path)
            await lim.init()
            await lim.set_first_seen(owner_id, platform, datetime.fromisoformat(now))

    async def list_accounts(self, owner_id: int, platform: str = None):
        async with aiosqlite.connect(self.db_path) as db:
            if platform:
                cur = await db.execute("SELECT platform, account_label, status FROM channel_accounts WHERE owner_id=? AND platform=?", (owner_id, platform))
            else:
                cur = await db.execute("SELECT platform, account_label, status FROM channel_accounts WHERE owner_id=?", (owner_id,))
            rows = await cur.fetchall()
            return [{"platform": r[0], "label": r[1], "status": r[2]} for r in rows]

    async def remove_account(self, owner_id: int, platform: str, label: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM channel_accounts WHERE owner_id=? AND platform=? AND account_label=?", (owner_id, platform, label))
            await db.commit()
