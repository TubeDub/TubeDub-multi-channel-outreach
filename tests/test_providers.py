import pytest, tempfile, os
import asyncio
from unittest.mock import AsyncMock, patch
from app.storage.database import init_db
from app.providers.telegram_provider import TelegramProvider
from app.providers.meta_messenger_provider import MetaMessengerProvider
from app.providers.email_provider import EmailProvider
from app.domain.errors import RateLimitError, ForbiddenError, ProviderError
from app.services.delivery_service import DeliveryService
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
async def test_telegram_check_connection_mock_success(db_path):
    prov = TelegramProvider(token="123:fake-token-for-test-abc12345678901234567890", db_path=db_path)
    from unittest.mock import MagicMock
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"ok": True, "result": {"username": "testbot", "first_name": "Test Bot", "id": 123}}
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False
    mock_client.get = AsyncMock(return_value=mock_resp)
    with patch("app.providers.telegram_provider.httpx.AsyncClient", return_value=mock_client):
        res = await prov.check_connection(owner_id=1)
        assert res["status"] == "connected"
        assert "testbot" in res["hint"]

@pytest.mark.asyncio
async def test_telegram_rate_limit_handling(db_path):
    prov = TelegramProvider(token="123:fake-token-abc12345678901234567890", db_path=db_path)
    from unittest.mock import MagicMock
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"ok": False, "error_code": 429, "description": "Too Many Requests: retry after 5", "parameters": {"retry_after": 5}}
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False
    mock_client.post = AsyncMock(return_value=mock_resp)
    with patch("app.providers.telegram_provider.httpx.AsyncClient", return_value=mock_client):
        try:
            await prov.send_message("123", "hello", owner_id=1)
            assert False, "Should raise RateLimitError"
        except RateLimitError as e:
            assert e.retry_after == 5
        except ProviderError:
            pass

@pytest.mark.asyncio
async def test_telegram_forbidden_handling(db_path):
    prov = TelegramProvider(token="123:fake-token-abc12345678901234567890", db_path=db_path)
    from unittest.mock import MagicMock
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"ok": False, "error_code": 403, "description": "Forbidden: bot was blocked by the user"}
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False
    mock_client.post = AsyncMock(return_value=mock_resp)
    with patch("app.providers.telegram_provider.httpx.AsyncClient", return_value=mock_client):
        try:
            await prov.send_message("123", "hello")
            assert False
        except ForbiddenError:
            pass
        except ProviderError as e:
            assert "Forbidden" in str(e) or "403" in str(e)

@pytest.mark.asyncio
async def test_api_error_not_marked_as_sent(db_path):
    # Simulate delivery where API returns error -> delivery should be failed, not sent
    providers = {}
    # mock telegram provider that always fails with ProviderError
    class FailingProvider:
        platform="telegram"
        async def send_message(self, recipient, text, owner_id=None):
            raise ProviderError("Bad Request: chat not found", code="400")
        async def publish(self, chat_id, text, owner_id=None):
            raise ProviderError("Bad Request: chat not found", code="400")
        async def check_connection(self, owner_id=None):
            return {"status":"connected"}
        async def get_capabilities(self):
            return {}
        async def get_default_channel(self, owner_id):
            return None
    providers["telegram"] = FailingProvider()
    svc = DeliveryService(db_path, providers)
    from app.storage.repositories import CampaignRepo
    from app.services.campaign_service import CampaignService
    camp_svc = CampaignService(db_path)
    c = Campaign(owner_id=1, platform="telegram", campaign_type="audience_message", country="Украина", message_text="valid text for test", requested_limit=2, audience_source="bot_subscribers")
    created = await camp_svc.create_draft(c)
    # manually inject consented contacts
    from app.services.consent_service import ConsentService
    cs = ConsentService(db_path)
    await cs.grant(1, "telegram", "111", source="test")
    await cs.grant(1, "telegram", "222", source="test")
    from app.services.audience_service import AudienceService
    aud = AudienceService(db_path)
    recips = await aud.resolve_recipients(created)
    assert len(recips) == 2
    await svc.prepare_queue(created, recips)
    await svc.run_campaign(created)
    from app.storage.repositories import DeliveryRepo
    repo = DeliveryRepo(db_path)
    stats = await repo.stats(created.id)
    # Should be failed, not sent
    assert stats.get("sent", 0) == 0
    assert stats.get("failed", 0) == 2
    # campaign should be failed (since all failed)
    final = await CampaignRepo(db_path).get(created.id)
    assert final.status == "failed"

@pytest.mark.asyncio
async def test_unsubscribed_skipped_not_failed(db_path):
    # Provider success but one recipient revoked
    class SuccessProvider:
        platform="telegram"
        async def send_message(self, recipient, text, owner_id=None):
            return {"message_id": 999}
        async def publish(self, chat_id, text, owner_id=None):
            return {"message_id": 999}
        async def check_connection(self, owner_id=None):
            return {"status":"connected"}
        async def get_capabilities(self):
            return {}
        async def get_default_channel(self, owner_id):
            return None
    providers = {"telegram": SuccessProvider()}
    svc = DeliveryService(db_path, providers)
    from app.services.campaign_service import CampaignService
    camp_svc = CampaignService(db_path)
    c = Campaign(owner_id=2, platform="telegram", campaign_type="audience_message", country="Украина", message_text="valid text hello", requested_limit=5, audience_source="bot_subscribers")
    created = await camp_svc.create_draft(c)
    from app.services.consent_service import ConsentService
    cs = ConsentService(db_path)
    await cs.grant(2, "telegram", "333", source="test")
    await cs.grant(2, "telegram", "444", source="test")
    await cs.revoke(2, "telegram", "444")
    from app.services.audience_service import AudienceService
    aud = AudienceService(db_path)
    recips = await aud.resolve_recipients(created)  # should only return 333 (consented)
    assert "333" in recips
    assert "444" not in recips
    # Manually create deliveries including revoked to test skip logic inside run_campaign
    from app.storage.repositories import DeliveryRepo
    from app.domain.models import Delivery
    d_repo = DeliveryRepo(db_path)
    await d_repo.create_many([Delivery(campaign_id=created.id, recipient="333", status="pending"), Delivery(campaign_id=created.id, recipient="444", status="pending")])
    created.status = "running"
    await camp_svc.repo.update(created)
    await svc.run_campaign(created)
    stats = await d_repo.stats(created.id)
    assert stats.get("sent",0) == 1
    assert stats.get("skipped",0) == 1

@pytest.mark.asyncio
async def test_other_providers_show_not_connected():
    for ProvCls in [MetaMessengerProvider]:
        prov = ProvCls(db_path=":memory:")
        res = await prov.check_connection(owner_id=1)
        assert res["status"] in ("not_connected","needs_permissions","unavailable")
        try:
            await prov.send_message("x","hello")
            assert False
        except ProviderError as e:
            assert "не подключ" in str(e).lower() or "not_connected" in str(e).lower() or "не настроен" in str(e).lower()
    # email separately: test invalid email vs not_connected
    prov = EmailProvider(db_path=":memory:")
    res = await prov.check_connection(owner_id=1)
    assert res["status"] in ("not_connected","needs_permissions","unavailable")
    try:
        await prov.send_message("test@example.com","hello")
        assert False
    except ProviderError as e:
        assert "не подключ" in str(e).lower() or "not_connected" in str(e).lower() or "не настроен" in str(e).lower() or "некорректный" in str(e).lower()
    # invalid email should still raise ProviderError
    try:
        await prov.send_message("x","hello")
        assert False
    except ProviderError:
        pass

@pytest.mark.asyncio
async def test_no_secrets_in_logs(caplog=None):
    # Ensure token masking function works
    from app.config import mask_token
    assert mask_token("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11") == "1234***ew11"
    assert mask_token("") == "не настроен"
    # SecretFilter should mask tokens
    import logging
    from app.observability.logging_config import SecretFilter
    f = SecretFilter()
    rec = logging.LogRecord(name="test", level=logging.INFO, pathname="", lineno=0, msg="token 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11 exposed", args=(), exc_info=None)
    f.filter(rec)
    assert "***TOKEN***" in rec.msg or "ABC" not in rec.msg
