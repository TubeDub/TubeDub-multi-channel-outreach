import aiosqlite
import os
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

SCHEMA_SQL_BASE = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL,
    platform TEXT NOT NULL,
    campaign_type TEXT NOT NULL DEFAULT 'own_channel_post',
    country TEXT DEFAULT '',
    city TEXT DEFAULT '',
    audience_source TEXT DEFAULT 'bot_subscribers',
    audience_mode TEXT DEFAULT 'subscribers',
    requested_limit INTEGER DEFAULT 0,
    message_text TEXT DEFAULT '',
    link TEXT DEFAULT '',
    schedule_at TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    idempotency_key TEXT,
    recipients_json TEXT DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL,
    provider TEXT NOT NULL,
    external_id TEXT NOT NULL,
    consent_status TEXT NOT NULL DEFAULT 'granted',
    consent_source TEXT DEFAULT '',
    consent_at TEXT,
    unsubscribed_at TEXT,
    display_name TEXT DEFAULT '',
    UNIQUE(owner_id, provider, external_id)
);
CREATE TABLE IF NOT EXISTS deliveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    recipient TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER DEFAULT 0,
    provider_message_id TEXT,
    error_code TEXT,
    error_text TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL,
    campaign_id INTEGER,
    event TEXT NOT NULL,
    details TEXT DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    owner_id INTEGER PRIMARY KEY,
    default_country TEXT DEFAULT '',
    timezone TEXT DEFAULT 'Europe/Kiev',
    test_mode INTEGER DEFAULT 1,
    notifications INTEGER DEFAULT 1,
    queue_limit INTEGER DEFAULT 100,
    language TEXT DEFAULT 'ru'
);
CREATE TABLE IF NOT EXISTS provider_connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL,
    provider TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'not_connected',
    meta TEXT DEFAULT '',
    updated_at TEXT NOT NULL,
    UNIQUE(owner_id, provider)
);
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT DEFAULT '',
    first_name TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    free_used INTEGER NOT NULL DEFAULT 0,
    free_total INTEGER NOT NULL DEFAULT 10,
    subscription_status TEXT NOT NULL DEFAULT 'free',
    subscription_expires_at TEXT,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS payment_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    amount_usd REAL NOT NULL DEFAULT 1,
    period_days INTEGER NOT NULL DEFAULT 30,
    payment_mode TEXT DEFAULT 'manual_placeholder',
    card_last4 TEXT DEFAULT '',
    admin_id INTEGER,
    reviewed_at TEXT,
    details TEXT DEFAULT ''
);
"""

SCHEMA_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_campaigns_owner ON campaigns(owner_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_campaign ON deliveries(campaign_id);
CREATE INDEX IF NOT EXISTS idx_activity_owner ON activity(owner_id);
CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(subscription_status);
CREATE INDEX IF NOT EXISTS idx_payment_requests_user ON payment_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_requests_status ON payment_requests(status);
"""

async def init_db(db_path: str):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(SCHEMA_SQL_BASE)
        await db.commit()
        await _migrate_legacy(db)
        await _migrate_subscription(db)
        await _migrate_i18n(db)
        try:
            await db.executescript(SCHEMA_INDEXES)
            await db.commit()
        except Exception:
            pass

async def _migrate_legacy(db):
    try:
        cursor = await db.execute("PRAGMA table_info(campaigns)")
        cols = [r[1] for r in await cursor.fetchall()]
        now = datetime.now(timezone.utc).isoformat()
        if "user_id" in cols and "owner_id" not in cols:
            await db.execute("ALTER TABLE campaigns RENAME COLUMN user_id TO owner_id")
            cols = [c if c != "user_id" else "owner_id" for c in cols]
            await db.commit()
        additions = {
            "campaign_type": "TEXT DEFAULT 'own_channel_post'",
            "audience_source": "TEXT DEFAULT 'bot_subscribers'",
            "audience_mode": "TEXT DEFAULT 'subscribers'",
            "requested_limit": "INTEGER DEFAULT 0",
            "schedule_at": "TEXT",
            "updated_at": f"TEXT DEFAULT '{now}'",
            "idempotency_key": "TEXT",
            "message_text": "TEXT DEFAULT ''",
            "link": "TEXT DEFAULT ''",
        }
        if "audience_type" in cols and "audience_mode" not in cols:
            await db.execute("ALTER TABLE campaigns RENAME COLUMN audience_type TO audience_mode")
            await db.commit()
            cols.remove("audience_type")
            cols.append("audience_mode")
        if "count" in cols and "requested_limit" not in cols:
            await db.execute("ALTER TABLE campaigns RENAME COLUMN count TO requested_limit")
            await db.commit()
            cols.remove("count")
            cols.append("requested_limit")
        if "message" in cols and "message_text" not in cols:
            await db.execute("ALTER TABLE campaigns RENAME COLUMN message TO message_text")
            await db.commit()
            cols.remove("message")
            cols.append("message_text")
        for col, decl in additions.items():
            if col not in cols:
                await db.execute(f"ALTER TABLE campaigns ADD COLUMN {col} {decl}")
        await db.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Migration warning: {e}")

async def _migrate_i18n(db):
    try:
        cursor = await db.execute("PRAGMA table_info(settings)")
        cols = [r[1] for r in await cursor.fetchall()]
        if "language" not in cols and cols:
            await db.execute("ALTER TABLE settings ADD COLUMN language TEXT DEFAULT 'ru'")
            await db.commit()
        cursor = await db.execute("PRAGMA table_info(users)")
        cols2 = [r[1] for r in await cursor.fetchall()]
        if "language" not in cols2 and cols2:
            await db.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'ru'")
            await db.commit()
        # deliveries: расширить статусы — добавляем новые колонки для честной статистики
        cursor = await db.execute("PRAGMA table_info(deliveries)")
        cols3 = [r[1] for r in await cursor.fetchall()]
        if "next_retry_at" not in cols3 and cols3:
            await db.execute("ALTER TABLE deliveries ADD COLUMN next_retry_at TEXT")
            await db.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"i18n migration warning: {e}")

async def _migrate_subscription(db):
    """Миграция для системы подписок — добавляет недостающие колонки/таблицы"""
    try:
        cursor = await db.execute("PRAGMA table_info(users)")
        cols = [r[1] for r in await cursor.fetchall()]
        now = datetime.now(timezone.utc).isoformat()
        expected = {
            "free_used": "INTEGER NOT NULL DEFAULT 0",
            "free_total": "INTEGER NOT NULL DEFAULT 10",
            "subscription_status": "TEXT NOT NULL DEFAULT 'free'",
            "subscription_expires_at": "TEXT",
            "updated_at": f"TEXT NOT NULL DEFAULT '{now}'",
            "username": "TEXT DEFAULT ''",
            "first_name": "TEXT DEFAULT ''",
        }
        for col, decl in expected.items():
            if col not in cols and cols:
                await db.execute(f"ALTER TABLE users ADD COLUMN {col} {decl}")
        cursor = await db.execute("PRAGMA table_info(payment_requests)")
        cols2 = [r[1] for r in await cursor.fetchall()]
        if cols2:
            if "admin_id" not in cols2:
                await db.execute("ALTER TABLE payment_requests ADD COLUMN admin_id INTEGER")
            if "reviewed_at" not in cols2:
                await db.execute("ALTER TABLE payment_requests ADD COLUMN reviewed_at TEXT")
        # campaigns recipients_json
        cursor = await db.execute("PRAGMA table_info(campaigns)")
        cols3 = [r[1] for r in await cursor.fetchall()]
        if "recipients_json" not in cols3:
            await db.execute("ALTER TABLE campaigns ADD COLUMN recipients_json TEXT DEFAULT '[]'")
        await db.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Subscription migration warning: {e}")

def backup_db(src_path: str, dst_dir: str = "backups"):
    Path(dst_dir).mkdir(parents=True, exist_ok=True)
    if not os.path.exists(src_path):
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = Path(dst_dir) / f"backup_{ts}.db"
    shutil.copy2(src_path, dst)
    return str(dst)

def get_connection(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

async def get_async_connection(db_path: str):
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    return db
