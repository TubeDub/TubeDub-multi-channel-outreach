import pytest
import tempfile, os, asyncio
from app.storage.database import init_db

@pytest.mark.asyncio
async def test_telegram_user_provider_honest_statuses():
    from app.providers.telegram_user_provider import TelegramUserProvider
    p = TelegramUserProvider(db_path=":memory:")
    # без ключей -> not_connected/configuration_error, не падает
    r = await p.check_connection(owner_id=1)
    assert r["status"] in ("not_connected","configuration_error")
    assert "next_step" in r or "hint" in r
    # send without connection -> raises ProviderError with code
    from app.domain.errors import ProviderError
    with pytest.raises(ProviderError) as exc:
        await p.send_message(recipient="111", text="hi", owner_id=1)
    assert exc.value.code in ("not_connected","configuration_error","permission_error","service_error")

@pytest.mark.asyncio
async def test_audience_import_dedup():
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    path = tmp.name
    await init_db(path)
    from app.services.audience_import_service import AudienceImportService
    svc = AudienceImportService(path)
    csv_data = b"external_id,provider,display_name\n+380501111111,whatsapp,Ivan\n+380501111111,whatsapp,Ivan\nuser@example.com,email,Maria\ninvalid_email,email,Bad\n"
    imported, dups, errors = await svc.import_csv(1, csv_data, filename="test.csv")
    assert imported == 2
    assert dups == 1
    assert len(errors) == 1  # invalid email
    contacts = await svc.list_contacts(1)
    assert len(contacts) == 2
    os.unlink(path)

@pytest.mark.asyncio
async def test_wizard_has_nine_steps():
    from app.bot.handlers.wizard import STEPS, STEP_TITLES
    assert len(STEPS) == 9, f"Мастер должен иметь 9 шагов, сейчас {len(STEPS)}"
    assert "platform" in STEPS
    assert "campaign_type" in STEPS
    assert "preview" in STEPS
    assert "schedule" in STEPS
    for s in STEPS:
        assert s in STEP_TITLES

@pytest.mark.asyncio
async def test_main_menu_has_accounts_and_audiences():
    from app.bot.keyboards import main_menu_keyboard
    kb = main_menu_keyboard("ru")
    flat = [btn.text if hasattr(btn,'text') else str(btn) for row in kb.keyboard for btn in row]
    joined = " ".join(flat)
    assert "Мои аккаунты" in joined or "Аккаунты" in joined
    assert "Аудитории" in joined
    assert "История" in joined or "Отчёты" in joined

@pytest.mark.asyncio
async def test_rate_limits_per_channel_not_bypassed():
    from app.services.delivery_service import RATE_LIMITS
    assert "telegram_user" in RATE_LIMITS
    assert RATE_LIMITS["telegram_user"] >= 0.5
    assert RATE_LIMITS["telegram"] >= 0.5
    # не равны 0, честно соблюдаются
    for plat, delay in RATE_LIMITS.items():
        assert delay > 0

@pytest.mark.asyncio
async def test_provider_isolation():
    from app.providers.meta_messenger_provider import MetaMessengerProvider
    from app.providers.telegram_provider import TelegramProvider
    # отсутствие токена Messenger не ломает Telegram
    m = MetaMessengerProvider(db_path=":memory:")
    r1 = await m.check_connection(owner_id=1)
    assert r1["status"] == "not_connected"
    t = TelegramProvider(db_path=":memory:")
    r2 = await t.check_connection(owner_id=1)
    # telegram без токена -> configuration_error/not_connected/permission_error, не exception (изоляция)
    assert r2["status"] in ("configuration_error","not_connected","service_error","permission_error")
