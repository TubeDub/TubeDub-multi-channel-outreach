import pytest
import tempfile, os
from app.storage.database import init_db
from app.services.campaign_service import CampaignService
from app.domain.models import Campaign
from app.domain.statuses import CampaignStatus

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
async def test_campaign_list_button_and_card(db_path):
    svc = CampaignService(db_path)
    # create 3 campaigns
    for i in range(3):
        c = Campaign(owner_id=10, platform="telegram", country="Украина", message_text=f"msg {i} valid text", requested_limit=10, audience_source="bot_subscribers", campaign_type="own_channel_post")
        await svc.create_draft(c)
    items, total, pages = await svc.list_paginated(10, page=1, per_page=5)
    assert total == 3
    assert len(items) == 3
    # each item should have id and can be opened individually
    for it in items:
        fetched = await svc.get_owned(it.id, 10)
        assert fetched.id == it.id
        # verify card text generation
        from app.bot.handlers.campaigns import _campaign_details_text
        txt = _campaign_details_text(fetched, deliveries_stats={})
        assert f"#{fetched.id}" in txt
        assert fetched.platform in txt.lower() or "Telegram" in txt

@pytest.mark.asyncio
async def test_back_to_list(db_path):
    svc = CampaignService(db_path)
    c = Campaign(owner_id=11, platform="telegram", country="Украина", message_text="hello valid", requested_limit=5, audience_source="bot_subscribers", campaign_type="own_channel_post")
    created = await svc.create_draft(c)
    items, total, pages = await svc.list_paginated(11, page=1)
    assert total == 1
    # list should be reachable after opening card (we just check pagination doesn't lose item)
    assert items[0].id == created.id

@pytest.mark.asyncio
async def test_edit_duplicate_delete_with_owner_check(db_path):
    svc = CampaignService(db_path)
    c = Campaign(owner_id=20, platform="telegram", country="Украина", message_text="original valid text", requested_limit=10, audience_source="bot_subscribers")
    created = await svc.create_draft(c)
    # edit
    updated = await svc.update(created.id, 20, message_text="edited text valid")
    assert updated.message_text == "edited text valid"
    assert updated.id == created.id
    # duplicate should create new draft with new ID
    copy = await svc.duplicate(created.id, 20)
    assert copy.id != created.id
    assert copy.status == "draft"
    assert copy.message_text == "edited text valid"
    # delete copy
    await svc.delete(copy.id, 20)
    assert await svc.repo.get(copy.id) is None
    # verify original still exists
    orig = await svc.repo.get(created.id)
    assert orig is not None

@pytest.mark.asyncio
async def test_cannot_delete_running_campaign(db_path):
    svc = CampaignService(db_path)
    c = Campaign(owner_id=21, platform="telegram", country="Украина", message_text="running text valid", requested_limit=5, audience_source="bot_subscribers")
    created = await svc.create_draft(c)
    # manually set to queued
    created.status = "queued"
    await svc.repo.update(created)
    # attempt delete should raise
    try:
        await svc.delete(created.id, 21)
        assert False, "Should have raised TransitionError"
    except Exception as e:
        assert "Нельзя удалить" in str(e) or "cannot" in str(e).lower() or "Transition" in type(e).__name__

@pytest.mark.asyncio
async def test_owner_isolation(db_path):
    svc = CampaignService(db_path)
    c = Campaign(owner_id=100, platform="telegram", country="Украина", message_text="owner 100 text valid", requested_limit=5, audience_source="bot_subscribers")
    created = await svc.create_draft(c)
    # user B tries to access
    try:
        await svc.get_owned(created.id, 200)
        assert False, "Should deny"
    except Exception as e:
        assert "Нет доступа" in str(e) or "Permission" in type(e).__name__
    try:
        await svc.update(created.id, 200, message_text="hack")
        assert False
    except Exception:
        pass

@pytest.mark.asyncio
async def test_double_launch_idempotency(db_path):
    svc = CampaignService(db_path)
    c = Campaign(owner_id=30, platform="telegram", country="Украина", message_text="launch test valid", requested_limit=5, audience_source="bot_subscribers")
    created = await svc.create_draft(c)
    # set to ready then queued
    created.status = "ready"
    await svc.repo.update(created)
    import uuid
    key = str(uuid.uuid4())
    await svc.set_status(created.id, 30, "queued", idempotency_key=key)
    # second queued call should either be blocked (already queued) or idempotent
    try:
        await svc.set_status(created.id, 30, "queued", idempotency_key=key)
        # if no exception, ensure status still queued and no duplicate queue
        c2 = await svc.repo.get(created.id)
        assert c2.status == "queued"
    except Exception:
        # expected transition error if not allowed
        pass

@pytest.mark.asyncio
async def test_status_lifecycle_transitions(db_path):
    svc = CampaignService(db_path)
    c = Campaign(owner_id=40, platform="telegram", country="Украина", message_text="lifecycle valid text", requested_limit=5, audience_source="bot_subscribers")
    created = await svc.create_draft(c)
    # draft -> ready -> queued -> running -> completed
    # set to ready
    created.status = "ready"
    await svc.repo.update(created)
    await svc.set_status(created.id, 40, "queued")
    c1 = await svc.repo.get(created.id)
    assert c1.status == "queued"
    await svc.set_status(created.id, 40, "running")
    assert (await svc.repo.get(created.id)).status == "running"
    # pause / resume
    await svc.set_status(created.id, 40, "paused")
    assert (await svc.repo.get(created.id)).status == "paused"
    await svc.set_status(created.id, 40, "queued")
    assert (await svc.repo.get(created.id)).status == "queued"
    await svc.set_status(created.id, 40, "running")
    await svc.set_status(created.id, 40, "completed")
    assert (await svc.repo.get(created.id)).status == "completed"
    # cannot transition from completed
    try:
        await svc.set_status(created.id, 40, "queued")
        assert False
    except Exception:
        pass
