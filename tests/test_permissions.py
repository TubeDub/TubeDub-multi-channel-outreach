import pytest, tempfile, os
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
async def test_user_a_cannot_open_b_campaign_via_callback_id(db_path):
    svc = CampaignService(db_path)
    c = Campaign(owner_id=1, platform="telegram", country="Украина", message_text="secret valid", requested_limit=5, audience_source="bot_subscribers")
    created = await svc.create_draft(c)
    # attacker tries to open with their own owner_id but spoofing callback ID
    try:
        await svc.get_owned(created.id, 2)
        assert False, "Must deny access when owner_id mismatched"
    except Exception as e:
        assert "Нет доступа" in str(e) or "Permission" in type(e).__name__

@pytest.mark.asyncio
async def test_all_status_dependent_buttons_have_handlers(db_path):
    # Ensure keyboard generation doesn't crash for each status and includes proper callbacks
    from app.bot.keyboards import campaign_card_keyboard
    from app.domain.models import Campaign
    for status in ["draft","needs_setup","ready","queued","running","paused","completed","failed","cancelled"]:
        c = Campaign(id=123, owner_id=1, platform="telegram", country="UA", city="", status=status, message_text="x"*10, link="")
        kb = campaign_card_keyboard(c)
        # Should contain at least one button
        assert kb.inline_keyboard
        # All callbacks should be known patterns
        known_prefixes = ("camp_view","camp_edit","camp_dup","camp_run","camp_pause","camp_resume","camp_cancel","camp_del","camp_list","go_menu","camp_open")
        for row in kb.inline_keyboard:
            for btn in row:
                assert any(btn.callback_data.startswith(p) or btn.callback_data=="go_menu" for p in known_prefixes), f"Unknown callback {btn.callback_data}"

@pytest.mark.asyncio
async def test_launch_blocked_without_connection(db_path):
    svc = CampaignService(db_path)
    c = Campaign(owner_id=50, platform="facebook_messenger", country="Украина", message_text="test valid text", requested_limit=5, audience_source="bot_subscribers")
    created = await svc.create_draft(c)
    async def fake_checker(platform, owner_id):
        return {"status": "not_connected", "hint": "Meta token missing"}
    ok, reasons = await svc.check_readiness(created.id, 50, fake_checker)
    assert not ok
    assert any("не подключ" in r.lower() or "not_connected" in r.lower() for r in reasons)

@pytest.mark.asyncio
async def test_suppression_list_skips_unsubscribed():
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    path = tmp.name
    await init_db(path)
    from app.services.consent_service import ConsentService
    from app.storage.repositories import ContactRepo
    cs = ConsentService(path)
    await cs.grant(10, "telegram", "1001", source="test")
    await cs.grant(10, "telegram", "1002", source="test")
    # user 1002 unsubscribes
    await cs.revoke(10, "telegram", "1002")
    assert await cs.is_consented(10, "telegram", "1001") == True
    assert await cs.is_consented(10, "telegram", "1002") == False
    os.unlink(path)
