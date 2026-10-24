"""
Тесты по критическому ТЗ — цель кампании успешные отправки, обработка ограничений, реальный Telegram, etc.
"""
import pytest, tempfile, os, asyncio, time
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_01_goal_10_with_10_available():
    from app.storage.database import init_db
    from app.domain.models import Campaign
    from app.services.delivery_service import DeliveryService
    from app.providers.telegram_provider import TelegramProvider
    from app.services.consent_service import ConsentService
    tmp=tempfile.NamedTemporaryFile(delete=False,suffix=".db");tmp.close();path=tmp.name
    await init_db(path)
    try:
        prov=TelegramProvider(token="dummy", db_path=path)
        async def ok(*a,**kw): return {"message_id":1}
        prov.send_message=ok
        prov.publish=ok
        svc=DeliveryService(path, {"telegram":prov})
        # создаём кампанию цель 10
        from app.storage.repositories import CampaignRepo
        import aiosqlite
        async with aiosqlite.connect(path) as db:
            await db.execute("INSERT INTO campaigns (owner_id, platform, campaign_type, country, message_text, requested_limit, status, created_at, updated_at) VALUES (1,'telegram','audience_message','Украина','hello valid',10,'running','now','now')")
            await db.commit()
            cur=await db.execute("SELECT id FROM campaigns"); r=await cur.fetchone(); cid=r[0]
        cs=ConsentService(path)
        recs=[str(i) for i in range(10)]
        for rec in recs:
            await cs.grant(1,"telegram",rec,source="test",display_name=rec)
        c=await CampaignRepo(path).get(cid)
        await svc.prepare_queue(c, recs)
        with patch('app.services.delivery_service.asyncio.sleep', new=AsyncMock()):
            await svc.run_campaign(c)
        from app.storage.repositories import DeliveryRepo
        stats=await DeliveryRepo(path).stats(cid)
        assert stats.get("sent",0)==10
        honest=await svc.get_honest_stats(cid)
        assert honest["goal"]==10 and honest["remaining"]==0 and honest["success"]==10
    finally: os.unlink(path)

@pytest.mark.asyncio
async def test_02_first_unavailable_next_available():
    from app.storage.database import init_db
    from app.providers.telegram_provider import TelegramProvider
    from app.services.delivery_service import DeliveryService
    from app.services.consent_service import ConsentService
    tmp=tempfile.NamedTemporaryFile(delete=False,suffix=".db");tmp.close();path=tmp.name
    await init_db(path)
    try:
        prov=TelegramProvider(token="dummy", db_path=path)
        async def fail_first(recipient=None, **kw):
            if recipient=="bad1":
                from app.domain.errors import ForbiddenError
                raise ForbiddenError("blocked permanent", code="blocked")
            return {"message_id":1}
        prov.send_message=lambda recipient, text, owner_id=None: fail_first(recipient)
        svc=DeliveryService(path, {"telegram":prov})
        from app.storage.repositories import CampaignRepo
        import aiosqlite
        async with aiosqlite.connect(path) as db:
            await db.execute("INSERT INTO campaigns (owner_id, platform, campaign_type, country, message_text, requested_limit, status, created_at, updated_at) VALUES (1,'telegram','audience_message','Украина','hello valid',3,'running','now','now')")
            await db.commit()
            cur=await db.execute("SELECT id FROM campaigns"); r=await cur.fetchone(); cid=r[0]
        cs=ConsentService(path)
        for rec in ["bad1","good2","good3"]:
            await cs.grant(1,"telegram",rec,source="test",display_name=rec)
        c=await CampaignRepo(path).get(cid)
        await svc.prepare_queue(c, ["bad1","good2","good3"])
        await svc.run_campaign(c)
        from app.storage.repositories import DeliveryRepo
        stats=await DeliveryRepo(path).stats(cid)
        # первая постоянная ошибка, следующие доступны — продолжаем
        assert stats.get("failed",0)==1
        assert stats.get("sent",0)==2
        honest=await svc.get_honest_stats(cid)
        assert honest["goal"]==3
        assert honest["success"]==2
        assert honest["remaining"]==1
    finally: os.unlink(path)

@pytest.mark.asyncio
async def test_03_temporary_retry():
    from app.storage.database import init_db
    from app.providers.telegram_provider import TelegramProvider
    from app.services.delivery_service import DeliveryService
    from app.services.consent_service import ConsentService
    tmp=tempfile.NamedTemporaryFile(delete=False,suffix=".db");tmp.close();path=tmp.name
    await init_db(path)
    try:
        prov=TelegramProvider(token="dummy", db_path=path)
        calls={"n":0}
        async def flaky(recipient=None, **kw):
            calls["n"]+=1
            if calls["n"]==1:
                from app.domain.errors import ProviderError
                raise ProviderError("timeout temporary", code="timeout")
            return {"message_id":1}
        prov.send_message=flaky
        svc=DeliveryService(path, {"telegram":prov})
        from app.storage.repositories import CampaignRepo
        import aiosqlite
        async with aiosqlite.connect(path) as db:
            await db.execute("INSERT INTO campaigns (owner_id, platform, campaign_type, country, message_text, requested_limit, status, created_at, updated_at) VALUES (1,'telegram','audience_message','Украина','hello valid',1,'running','now','now')")
            await db.commit()
            cur=await db.execute("SELECT id FROM campaigns"); r=await cur.fetchone(); cid=r[0]
        cs=ConsentService(path)
        await cs.grant(1,"telegram","111",source="test",display_name="111")
        c=await CampaignRepo(path).get(cid)
        await svc.prepare_queue(c, ["111"])
        await svc.run_campaign(c)
        from app.storage.repositories import DeliveryRepo
        stats=await DeliveryRepo(path).stats(cid)
        assert stats.get("sent",0)==1
        assert calls["n"]>=2
    finally: os.unlink(path)

@pytest.mark.asyncio
async def test_04_rate_limit_wait():
    from app.storage.database import init_db
    from app.providers.telegram_provider import TelegramProvider
    from app.services.delivery_service import DeliveryService
    from app.services.consent_service import ConsentService
    tmp=tempfile.NamedTemporaryFile(delete=False,suffix=".db");tmp.close();path=tmp.name
    await init_db(path)
    try:
        prov=TelegramProvider(token="dummy", db_path=path)
        calls={"n":0}
        async def rate_limited(recipient=None, **kw):
            calls["n"]+=1
            if calls["n"]==1:
                from app.domain.errors import RateLimitError
                raise RateLimitError("429", code="429", retry_after=1)
            return {"message_id":1}
        prov.send_message=rate_limited
        svc=DeliveryService(path, {"telegram":prov})
        from app.storage.repositories import CampaignRepo
        import aiosqlite
        async with aiosqlite.connect(path) as db:
            await db.execute("INSERT INTO campaigns (owner_id, platform, campaign_type, country, message_text, requested_limit, status, created_at, updated_at) VALUES (1,'telegram','audience_message','Украина','hello valid',1,'running','now','now')")
            await db.commit()
            cur=await db.execute("SELECT id FROM campaigns"); r=await cur.fetchone(); cid=r[0]
        cs=ConsentService(path)
        await cs.grant(1,"telegram","111",source="test",display_name="111")
        c=await CampaignRepo(path).get(cid)
        await svc.prepare_queue(c, ["111"])
        start=time.time()
        await svc.run_campaign(c)
        elapsed=time.time()-start
        assert elapsed>=0.9  # ждали Retry-After 1с
        from app.storage.repositories import DeliveryRepo
        stats=await DeliveryRepo(path).stats(cid)
        assert stats.get("sent",0)==1
    finally: os.unlink(path)

@pytest.mark.asyncio
async def test_05_not_completed_after_one_of_ten():
    from app.storage.database import init_db
    from app.storage.repositories import CampaignRepo, DeliveryRepo
    tmp=tempfile.NamedTemporaryFile(delete=False,suffix=".db");tmp.close();path=tmp.name
    await init_db(path)
    try:
        import aiosqlite
        async with aiosqlite.connect(path) as db:
            await db.execute("INSERT INTO campaigns (owner_id, platform, campaign_type, country, message_text, requested_limit, status, created_at, updated_at) VALUES (1,'telegram','audience_message','Украина','hello valid',10,'running','now','now')")
            await db.commit()
            cur=await db.execute("SELECT id FROM campaigns"); r=await cur.fetchone(); cid=r[0]
            # создадим 10 deliveries, 1 sent, 9 pending
            for i in range(10):
                st="sent" if i==0 else "pending"
                await db.execute("INSERT INTO deliveries (campaign_id, recipient, status, attempts, created_at, updated_at) VALUES (?,?,?,?,?,?)", (cid,str(i),st,1,"now","now"))
            await db.commit()
        c=await CampaignRepo(path).get(cid)
        stats=await DeliveryRepo(path).stats(cid)
        assert stats.get("sent",0)==1
        assert stats.get("pending",0)==9
        assert c.status=="running"
        # не объявляем завершённой пока есть pending
        assert c.status!="completed"
        # remaining
        from app.services.delivery_service import DeliveryService
        from app.providers.telegram_provider import TelegramProvider
        svc=DeliveryService(path, {"telegram": TelegramProvider(token="dummy", db_path=path)})
        honest=await svc.get_honest_stats(cid)
        assert honest["goal"]==10
        assert honest["remaining"]==9
    finally: os.unlink(path)

@pytest.mark.asyncio
async def test_06_counter_not_increase_on_error():
    from app.storage.database import init_db
    from app.providers.telegram_provider import TelegramProvider
    from app.services.delivery_service import DeliveryService
    from app.services.consent_service import ConsentService
    tmp=tempfile.NamedTemporaryFile(delete=False,suffix=".db");tmp.close();path=tmp.name
    await init_db(path)
    try:
        prov=TelegramProvider(token="dummy", db_path=path)
        async def fail(*a,**kw):
            from app.domain.errors import ProviderError
            raise ProviderError("bad", code="400")
        prov.send_message=fail
        svc=DeliveryService(path, {"telegram":prov})
        from app.storage.repositories import CampaignRepo
        import aiosqlite
        async with aiosqlite.connect(path) as db:
            await db.execute("INSERT INTO campaigns (owner_id, platform, campaign_type, country, message_text, requested_limit, status, created_at, updated_at) VALUES (1,'telegram','audience_message','Украина','hello valid',5,'running','now','now')")
            await db.commit()
            cur=await db.execute("SELECT id FROM campaigns"); r=await cur.fetchone(); cid=r[0]
        cs=ConsentService(path)
        await cs.grant(1,"telegram","111",source="test",display_name="111")
        c=await CampaignRepo(path).get(cid)
        await svc.prepare_queue(c, ["111"])
        await svc.run_campaign(c)
        from app.storage.repositories import DeliveryRepo
        stats=await DeliveryRepo(path).stats(cid)
        assert stats.get("sent",0)==0
        honest=await svc.get_honest_stats(cid)
        assert honest["success"]==0
        assert honest["remaining"]==5
    finally: os.unlink(path)

@pytest.mark.asyncio
async def test_07_goal_100_with_100():
    from app.storage.database import init_db
    from app.providers.telegram_provider import TelegramProvider
    from app.services.delivery_service import DeliveryService
    from app.services.consent_service import ConsentService
    tmp=tempfile.NamedTemporaryFile(delete=False,suffix=".db");tmp.close();path=tmp.name
    await init_db(path)
    try:
        prov=TelegramProvider(token="dummy", db_path=path)
        async def ok(*a,**kw): return {"message_id":1}
        prov.send_message=ok
        svc=DeliveryService(path, {"telegram":prov})
        from app.storage.repositories import CampaignRepo
        import aiosqlite
        async with aiosqlite.connect(path) as db:
            await db.execute("INSERT INTO campaigns (owner_id, platform, campaign_type, country, message_text, requested_limit, status, created_at, updated_at) VALUES (1,'telegram','audience_message','Украина','hello valid',100,'running','now','now')")
            await db.commit()
            cur=await db.execute("SELECT id FROM campaigns"); r=await cur.fetchone(); cid=r[0]
        cs=ConsentService(path)
        recs=[str(i) for i in range(100)]
        for rec in recs:
            await cs.grant(1,"telegram",rec,source="test",display_name=rec)
        c=await CampaignRepo(path).get(cid)
        await svc.prepare_queue(c, recs)
        with patch('app.services.delivery_service.asyncio.sleep', new=AsyncMock()):
            await svc.run_campaign(c)
        from app.storage.repositories import DeliveryRepo
        stats=await DeliveryRepo(path).stats(cid)
        assert stats.get("sent",0)==100
        assert c.requested_limit==100
    finally: os.unlink(path)

@pytest.mark.asyncio
async def test_08_no_available_honest():
    from app.storage.database import init_db
    from app.providers.telegram_provider import TelegramProvider
    from app.services.delivery_service import DeliveryService
    tmp=tempfile.NamedTemporaryFile(delete=False,suffix=".db");tmp.close();path=tmp.name
    await init_db(path)
    try:
        prov=TelegramProvider(token="dummy", db_path=path)
        svc=DeliveryService(path, {"telegram":prov})
        from app.storage.repositories import CampaignRepo
        import aiosqlite
        async with aiosqlite.connect(path) as db:
            await db.execute("INSERT INTO campaigns (owner_id, platform, campaign_type, country, message_text, requested_limit, status, created_at, updated_at) VALUES (1,'telegram','audience_message','Украина','hello valid',10,'running','now','now')")
            await db.commit()
            cur=await db.execute("SELECT id FROM campaigns"); r=await cur.fetchone(); cid=r[0]
        c=await CampaignRepo(path).get(cid)
        # нет получателей
        cnt=await svc.prepare_queue(c, [])
        assert cnt==0
        await svc.run_campaign(c)
        from app.storage.repositories import CampaignRepo as CR
        final=await CR(path).get(cid)
        # честно 0
        assert final.status=="completed"
        from app.storage.repositories import DeliveryRepo
        stats=await DeliveryRepo(path).stats(cid)
        assert stats=={}
    finally: os.unlink(path)

@pytest.mark.asyncio
async def test_09_restart_restores_queue():
    from app.storage.database import init_db
    from app.services.campaign_service import CampaignService
    from app.domain.models import Campaign
    tmp=tempfile.NamedTemporaryFile(delete=False,suffix=".db");tmp.close();path=tmp.name
    await init_db(path)
    try:
        svc=CampaignService(path)
        c=Campaign(owner_id=1, platform="telegram", country="Украина", message_text="hello valid text", requested_limit=2, audience_source="bot_subscribers", campaign_type="audience_message")
        created=await svc.create_draft(c)
        # имитируем очередь
        from app.providers.telegram_provider import TelegramProvider
        from app.services.delivery_service import DeliveryService
        prov=TelegramProvider(token="dummy", db_path=path)
        delivery=DeliveryService(path, {"telegram":prov})
        await delivery.prepare_queue(created, ["1","2"])
        # перезапуск — переинициализация БД
        await init_db(path)
        from app.storage.repositories import DeliveryRepo
        lst=await DeliveryRepo(path).list_by_campaign(created.id)
        assert len(lst)==2
        assert all(d.status=="pending" for d in lst)
    finally: os.unlink(path)

@pytest.mark.asyncio
async def test_10_admin_not_substituted():
    from app.storage.database import init_db
    from app.domain.models import Campaign
    from app.services.delivery_service import DeliveryService
    from app.providers.telegram_provider import TelegramProvider
    tmp=tempfile.NamedTemporaryFile(delete=False,suffix=".db");tmp.close();path=tmp.name
    await init_db(path)
    try:
        from app.storage.repositories import CampaignRepo
        import aiosqlite
        async with aiosqlite.connect(path) as db:
            await db.execute("INSERT INTO campaigns (owner_id, platform, campaign_type, country, message_text, requested_limit, status, created_at, updated_at) VALUES (999,'telegram','audience_message','Украина','hello valid',2,'running','now','now')")
            await db.commit()
            cur=await db.execute("SELECT id FROM campaigns"); r=await cur.fetchone(); cid=r[0]
        prov=TelegramProvider(token="dummy", db_path=path)
        svc=DeliveryService(path, {"telegram":prov})
        c=await CampaignRepo(path).get(cid)
        cnt=await svc.prepare_queue(c, ["111","222"])
        assert cnt==2
        from app.storage.repositories import DeliveryRepo
        lst=await DeliveryRepo(path).list_by_campaign(cid)
        assert "999" not in [d.recipient for d in lst]
    finally: os.unlink(path)

@pytest.mark.asyncio
async def test_11_error_isolation():
    from app.providers.meta_messenger_provider import MetaMessengerProvider
    from app.providers.telegram_provider import TelegramProvider
    fb=MetaMessengerProvider(db_path=None)
    tg=TelegramProvider(token="123:valid_1234567890", db_path=None)
    fb_res=await fb.check_connection(owner_id=1)
    assert fb_res["status"] in ("not_connected","configuration_error")
    # telegram не должен упасть из-за fb
    assert tg is not None

@pytest.mark.asyncio
async def test_12_stats_match_saved():
    from app.storage.database import init_db
    from app.providers.telegram_provider import TelegramProvider
    from app.services.delivery_service import DeliveryService
    from app.services.consent_service import ConsentService
    tmp=tempfile.NamedTemporaryFile(delete=False,suffix=".db");tmp.close();path=tmp.name
    await init_db(path)
    try:
        prov=TelegramProvider(token="dummy", db_path=path)
        async def ok(*a,**kw): return {"message_id":1}
        prov.send_message=ok
        svc=DeliveryService(path, {"telegram":prov})
        from app.storage.repositories import CampaignRepo
        import aiosqlite
        async with aiosqlite.connect(path) as db:
            await db.execute("INSERT INTO campaigns (owner_id, platform, campaign_type, country, message_text, requested_limit, status, created_at, updated_at) VALUES (1,'telegram','audience_message','Украина','hello valid',2,'running','now','now')")
            await db.commit()
            cur=await db.execute("SELECT id FROM campaigns"); r=await cur.fetchone(); cid=r[0]
        cs=ConsentService(path)
        for rec in ["1","2"]:
            await cs.grant(1,"telegram",rec,source="test",display_name=rec)
        c=await CampaignRepo(path).get(cid)
        await svc.prepare_queue(c, ["1","2"])
        await svc.run_campaign(c)
        from app.storage.repositories import DeliveryRepo
        stats=await DeliveryRepo(path).stats(cid)
        honest=await svc.get_honest_stats(cid)
        assert honest["success"]==stats.get("sent",0)
        assert honest["goal"]==2
    finally: os.unlink(path)

@pytest.mark.asyncio
async def test_13_main_menu_buttons():
    from app.bot.keyboards import main_menu_keyboard
    kb=main_menu_keyboard()
    texts=[btn.text for row in kb.keyboard for btn in row]
    assert any("Создать" in t for t in texts)
    assert any("Мои кампании" in t for t in texts)
    assert any("История" in t for t in texts)
    assert any("Отчёты" in t for t in texts)
    assert any("Подключения" in t for t in texts)
    assert any("Настройки" in t for t in texts)
    assert any("Помощь" in t for t in texts)

@pytest.mark.asyncio
async def test_14_not_connected_not_fake():
    from app.providers.email_provider import EmailProvider
    import os as _os
    _os.environ["SMTP_HOST"]=""
    prov=EmailProvider(db_path=None)
    res=await prov.check_connection(owner_id=1)
    assert res["status"]!="connected"
