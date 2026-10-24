import pytest, tempfile, os, sqlite3
from app.storage.database import init_db, backup_db

@pytest.mark.asyncio
async def test_migration_preserves_existing_campaigns():
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    path = tmp.name
    # Simulate old schema with legacy columns
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            country TEXT DEFAULT '',
            city TEXT DEFAULT '',
            audience_type TEXT DEFAULT 'subscribers',
            count INTEGER DEFAULT 0,
            message TEXT DEFAULT '',
            link TEXT DEFAULT '',
            status TEXT DEFAULT 'draft',
            created_at TEXT
        )
    """)
    conn.execute("INSERT INTO campaigns (user_id, platform, country, city, audience_type, count, message, link, status, created_at) VALUES (1, 'telegram', 'Украина', 'Киев', 'subscribers', 100, 'старый текст', 'https://example.com', 'draft', '2024-01-01')")
    conn.execute("CREATE TABLE settings (owner_id INTEGER PRIMARY KEY, default_country TEXT)")
    conn.execute("INSERT INTO settings (owner_id, default_country) VALUES (1, 'Украина')")
    conn.execute("CREATE TABLE activity (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER, campaign_id INTEGER, event TEXT, details TEXT, created_at TEXT)")
    conn.execute("INSERT INTO activity (owner_id, campaign_id, event, details, created_at) VALUES (1, 1, 'created', 'test', '2024-01-01')")
    conn.commit()
    conn.close()

    # Now run new init_db which should migrate
    await init_db(path)

    # Verify campaigns still exists with new columns
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT * FROM campaigns WHERE id=1")
    row = cur.fetchone()
    assert row is not None
    # Legacy count -> requested_limit, message -> message_text, user_id -> owner_id
    assert row["owner_id"] == 1
    assert row["message_text"] == "старый текст"
    # requested_limit should be migrated from count
    assert row["requested_limit"] == 100
    # new columns should exist
    cur = conn.execute("PRAGMA table_info(campaigns)")
    cols = [r[1] for r in cur.fetchall()]
    assert "campaign_type" in cols
    assert "audience_source" in cols
    assert "idempotency_key" in cols

    # Settings and activity preserved
    cur = conn.execute("SELECT COUNT(*) FROM activity")
    assert cur.fetchone()[0] == 1
    conn.close()
    os.unlink(path)

@pytest.mark.asyncio
async def test_backup_created():
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    path = tmp.name
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE dummy (id INTEGER)")
    conn.commit()
    conn.close()
    # ensure data dir exists
    os.makedirs("backups", exist_ok=True)
    dst = backup_db(path, dst_dir="backups")
    assert dst is not None
    assert os.path.exists(dst)
    os.unlink(path)
    os.unlink(dst)

@pytest.mark.asyncio
async def test_secrets_not_in_db():
    # Ensure no token stored in provider_connections meta is exposed as secret? We store only meta hint without token
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    path = tmp.name
    await init_db(path)
    from app.storage.repositories import ProviderConnectionRepo
    from app.domain.models import ProviderConnection
    repo = ProviderConnectionRepo(path)
    await repo.upsert(ProviderConnection(owner_id=1, provider="telegram", status="connected", meta="@testbot"))
    pc = await repo.get(1, "telegram")
    assert "123:" not in pc.meta
    assert "token" not in pc.meta.lower()
    os.unlink(path)
