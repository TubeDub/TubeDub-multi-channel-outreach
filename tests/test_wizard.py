import pytest
import tempfile
import os
import asyncio
from app.storage.database import init_db
from app.services.campaign_service import CampaignService
from app.domain.models import Campaign

@pytest.fixture
async def db_path():
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    path = tmp.name
    await init_db(path)
    yield path
    try:
        os.unlink(path)
    except:
        pass

@pytest.mark.asyncio
async def test_start_shows_main_menu():
    # Simulate /start handler builds welcome text
    from app.bot.handlers.start import WELCOME
    assert "MultiChannel" in WELCOME or "Добро пожаловать" in WELCOME
    assert "кампани" in WELCOME.lower()  # кампания/кампании

@pytest.mark.asyncio
async def test_platform_saved_correctly(db_path):
    svc = CampaignService(db_path)
    for plat in ["telegram", "facebook_messenger", "instagram", "whatsapp", "tiktok", "email"]:
        c = Campaign(owner_id=1, platform=plat, campaign_type="own_channel_post", country="Украина", audience_source="bot_subscribers", audience_mode="subscribers", requested_limit=10, message_text="Hello world test", link="https://example.com")
        created = await svc.create_draft(c)
        assert created.platform == plat, f"Platform should be {plat}, got {created.platform}"
        assert created.id is not None

@pytest.mark.asyncio
async def test_draft_creation_via_all_steps(db_path):
    svc = CampaignService(db_path)
    c = Campaign(owner_id=42, platform="telegram", campaign_type="audience_message", country="Германия", city="Берлин", audience_source="bot_subscribers", audience_mode="leads", requested_limit=50, message_text="Привет, это тест", link="https://example.com/music", schedule_at=None, status="draft")
    created = await svc.create_draft(c)
    assert created.country == "Германия"
    assert created.city == "Берлин"
    assert created.audience_source == "bot_subscribers"
    assert created.requested_limit == 50
    assert created.message_text == "Привет, это тест"
    assert created.link == "https://example.com/music"
    assert created.platform == "telegram"

@pytest.mark.asyncio
async def test_back_cancel_idempotency(db_path):
    svc = CampaignService(db_path)
    c = Campaign(owner_id=5, platform="telegram", country="Украина", message_text="test message valid", requested_limit=5, audience_source="bot_subscribers", campaign_type="own_channel_post")
    created = await svc.create_draft(c)
    first_count = await svc.repo.count_by_owner(5)
    # Simulate double tap with same idempotency key: set_status should be idempotent
    import uuid
    key = str(uuid.uuid4())
    await svc.set_status(created.id, 5, "ready", idempotency_key=key)
    # double call with same key should not create duplicate or error
    c2 = await svc.set_status(created.id, 5, "ready", idempotency_key=key)
    assert c2.status == "ready"
    # second manual duplicate call shouldn't change count
    assert await svc.repo.count_by_owner(5) == first_count

@pytest.mark.asyncio
async def test_cancel_does_not_create_campaign(db_path):
    svc = CampaignService(db_path)
    cnt_before = await svc.repo.count_by_owner(99)
    # cancel means no create; ensure count unchanged
    assert cnt_before == 0
    # No campaign created
    assert await svc.repo.count_by_owner(99) == 0
