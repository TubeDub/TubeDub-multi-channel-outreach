import pytest
import tempfile
import os
import sys

@pytest.mark.asyncio
async def test_no_import_nameerror():
    """Все модули должны импортироваться без NameError — исправление Instagram Dict"""
    modules = [
        "app.providers.instagram_provider",
        "app.providers.whatsapp_provider",
        "app.providers.tiktok_provider",
        "app.providers.telegram_provider",
        "app.providers.meta_messenger_provider",
        "app.providers.email_provider",
        "app.bot.handlers.start",
        "app.bot.handlers.wizard",
        "app.bot.handlers.campaigns",
        "app.bot.handlers.history",
        "app.bot.handlers.integrations",
        "app.bot.handlers.settings",
        "app.storage.database",
        "app.services.campaign_service",
        "app.__main__",
    ]
    for mod in modules:
        try:
            __import__(mod)
        except NameError as e:
            pytest.fail(f"NameError при импорте {mod}: {e}")
        except ModuleNotFoundError:
            # telegram may miss in CI, but should not be NameError
            pass
        except Exception as e:
            # other errors are not NameError, but we ensure no NameError
            if "NameError" in type(e).__name__:
                pytest.fail(str(e))

@pytest.mark.asyncio
async def test_app_initializes_without_instagram_token():
    """Отсутствие Instagram токена не ломает инициализацию приложения"""
    # Очистим env
    os.environ.pop("META_ACCESS_TOKEN", None)
    os.environ.pop("WHATSAPP_TOKEN", None)
    os.environ.pop("TIKTOK_ACCESS_TOKEN", None)
    os.environ.pop("SMTP_HOST", None)
    from app.providers.instagram_provider import InstagramProvider
    from app.providers.whatsapp_provider import WhatsAppProvider
    from app.providers.tiktok_provider import TikTokProvider
    from app.providers.meta_messenger_provider import MetaMessengerProvider
    from app.providers.email_provider import EmailProvider

    for Prov in [InstagramProvider, WhatsAppProvider, TikTokProvider, MetaMessengerProvider, EmailProvider]:
        p = Prov(db_path=":memory:")
        res = await p.check_connection(owner_id=1)
        assert res["status"] in ("not_connected", "needs_permissions", "unavailable", "connected")
        assert "status" in res and "hint" in res

@pytest.mark.asyncio
async def test_provider_error_does_not_crash_other_modules():
    """Ошибки одного провайдера изолированы — остальные продолжают работать"""
    from app.providers.instagram_provider import InstagramProvider
    from app.providers.telegram_provider import TelegramProvider
    # Instagram always raises on send
    inst = InstagramProvider()
    tel = TelegramProvider(token="dummy:fake_token_for_test_123456789012345")
    # Instagram should raise ProviderError
    try:
        await inst.send_message("123", "hello")
        pytest.fail("Instagram should raise ProviderError")
    except Exception as e:
        assert "не подключ" in str(e).lower() or "not_connected" in str(e).lower()

    # Telegram check should still work (returns not_connected or connected, not crash)
    res = await tel.check_connection(owner_id=1)
    assert "status" in res

@pytest.mark.asyncio
async def test_build_app_without_optional_tokens():
    """build_app должен импортироваться и создаваться без опциональных токенов"""
    # Убедиться, что app.__main__ не делает network вызов при импорте
    import os
    # сохраним токен
    old = os.environ.get("TELEGRAM_BOT_TOKEN")
    os.environ["TELEGRAM_BOT_TOKEN"] = "123456:TEST_TOKEN_FAKE_FOR_UNIT_TEST_1234567890"
    try:
        from app.__main__ import build_app
        # build_app требует token, но должен создаться без падения из-за Instagram
        app = build_app()
        assert app is not None
        # Проверим, что handlers зарегистрированы
        handlers = app.handlers
        assert len(handlers) > 0
    finally:
        if old is not None:
            os.environ["TELEGRAM_BOT_TOKEN"] = old
        else:
            os.environ.pop("TELEGRAM_BOT_TOKEN", None)

@pytest.mark.asyncio
async def test_failed_send_not_marked_as_success(tmp_db_path=None):
    """Неудачная отправка не должна помечаться как успешная — честная отчётность"""
    import tempfile
    from app.storage.database import init_db
    from app.domain.models import Campaign
    from app.services.campaign_service import CampaignService
    from app.services.delivery_service import DeliveryService

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    path = tmp.name
    await init_db(path)
    try:
        svc = CampaignService(path)
        c = Campaign(owner_id=1, platform="instagram", country="Украина", message_text="test fail not success", requested_limit=1, audience_source="bot_subscribers", campaign_type="audience_message")
        created = await svc.create_draft(c)
        # Instagram always fails
        from app.providers.instagram_provider import InstagramProvider
        from app.providers.telegram_provider import TelegramProvider
        providers = {
            "instagram": InstagramProvider(db_path=path),
            "telegram": TelegramProvider(token="dummy", db_path=path),
        }
        delivery = DeliveryService(path, providers)
        # создадим контакт с согласием, чтобы не было skipped а именно failed
        from app.services.consent_service import ConsentService
        cs = ConsentService(path)
        await cs.grant(1, "instagram", "123", source="test")
        await delivery.prepare_queue(created, ["123"])
        created.status = "running"
        await svc.repo.update(created)
        await delivery.run_campaign(created)
        from app.storage.repositories import DeliveryRepo, CampaignRepo
        repo = DeliveryRepo(path)
        stats = await repo.stats(created.id)
        assert stats.get("sent", 0) == 0, "Не должно быть sent при ошибке"
        assert stats.get("failed", 0) == 1
        final = await CampaignRepo(path).get(created.id)
        assert final.status in ("failed", "completed"), "Кампания должна завершиться failed/completed, не sent"
    finally:
        try:
            os.unlink(path)
        except:
            pass

@pytest.mark.asyncio
async def test_env_example_has_no_secrets():
    """В .env.example не должно быть реальных токенов"""
    import pathlib
    # найдём .env.example относительно проекта
    for p in pathlib.Path(".").rglob(".env.example"):
        text = p.read_text()
        # не должно содержать токен вида 123456:AA...
        import re
        assert not re.search(r"\d{6,}:[A-Za-z0-9_-]{20,}", text), f"Реальный токен найден в {p}: замаскируйте!"
        # TELEGRAM_BOT_TOKEN должен быть пустым
        assert "TELEGRAM_BOT_TOKEN=" in text
        # после = не должно быть значения (или только placeholder)
        for line in text.splitlines():
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                val = line.split("=",1)[1].strip()
                assert val == "" or val.startswith("#") or "YOUR" in val.upper() or "PLACEHOLDER" in val.upper(), f"TELEGRAM_BOT_TOKEN должен быть пустым, got: {val}"
        break

@pytest.mark.asyncio
async def test_database_preserved_after_migration():
    """База и кампании должны сохраняться после миграции"""
    import tempfile, sqlite3
    from app.storage.database import init_db
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    path = tmp.name
    # создадим старую схему
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE campaigns (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, platform TEXT, country TEXT, city TEXT, audience_type TEXT, count INTEGER, message TEXT, link TEXT, status TEXT, created_at TEXT)")
    conn.execute("INSERT INTO campaigns (user_id, platform, country, city, audience_type, count, message, link, status, created_at) VALUES (1, 'telegram', 'Украина', 'Киев', 'subscribers', 100, 'старый текст', 'https://example.com', 'draft', '2024-01-01')")
    conn.commit()
    conn.close()
    await init_db(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT * FROM campaigns WHERE id=1")
    row = cur.fetchone()
    assert row is not None, "Кампания должна сохраниться после миграции"
    assert row["owner_id"] == 1
    conn.close()
    os.unlink(path)
