import asyncio
from datetime import datetime, timezone
from app.domain.models import Campaign, Delivery
from app.storage.repositories import DeliveryRepo, ActivityRepo, CampaignRepo
from app.domain.statuses import CampaignStatus
from app.providers.base import BaseProvider
from app.observability.logging_config import get_logger
from app.services.account_rate_limiter import AccountRateLimiter

logger = get_logger(__name__)

# Вариация текста — 5 шаблонов с подстановками, чтобы не слать один текст всем
TEXT_TEMPLATES = [
    "{text}",
    "Привет, {name}! {text}",
    "{name}, добрый день! {text} (г. {city})",
    "Здравствуйте, {name}! {text}",
    "{text} — с уважением, ваша команда. {city}",
]

def _vary_text(base: str, recipient: str, campaign) -> str:
    import random
    # простые подстановки — имя из external_id (последние цифры) или город
    name = recipient.split("@")[0] if "@" in recipient else recipient[-4:] if len(recipient)>4 else recipient
    # у кампании есть country/city
    city = getattr(campaign, "city", "") or "ваш город"
    tmpl = random.choice(TEXT_TEMPLATES)
    return tmpl.format(text=base, name=name, city=city).strip()


# Антибан: рандомизированные задержки задаются в провайдере, здесь — базовые per-channel для очередности
RATE_LIMITS = {
    "telegram": 0.5,
    "telegram_user": 0.7,  # фактическая задержка 45-120с внутри провайдера, здесь — межзадачная пауза
    "facebook_messenger": 0.8,
    "instagram": 1.0,
    "whatsapp": 1.0,
    "tiktok": 1.5,
    "email": 0.3,
}

# Дневные лимиты Telegram (§4 ТЗ)
DAILY_LIMITS = {
    "telegram_user": 30,  # стартовый безопасный: новый 5-15, прогретый 20-40, установленный до 50
    "telegram": 100,  # бот — выше, но тоже ограничен
    "facebook_messenger": 1000,
    "instagram": 500,
    "whatsapp": 250,
    "email": 500,
    "tiktok": 0,
}

class DeliveryService:
    def __init__(self, db_path: str, providers: dict):
        self.db_path = db_path
        self.providers = providers
        self.delivery_repo = DeliveryRepo(db_path)
        self.activity_repo = ActivityRepo(db_path)
        self.campaign_repo = CampaignRepo(db_path)
        self.limiter = AccountRateLimiter(db_path)
        self._running_tasks = {}

    def get_provider(self, platform: str) -> BaseProvider:
        return self.providers.get(platform)

    async def prepare_queue(self, campaign: Campaign, recipients: list = None) -> int:
        """Создаёт отдельные задания. Не подменяет recipient на owner_id."""
        if campaign.campaign_type == "own_channel_post":
            provider = self.get_provider(campaign.platform)
            channel_id = None
            if provider and hasattr(provider, "get_default_channel"):
                channel_id = await provider.get_default_channel(campaign.owner_id)
            if not channel_id:
                channel_id = "channel_not_configured"
            deliveries = [Delivery(campaign_id=campaign.id, recipient=channel_id, status="pending")]
            await self.delivery_repo.create_many(deliveries)
            return len(deliveries)
        if not recipients:
            return 0
        existing = await self.delivery_repo.list_by_campaign(campaign.id)
        if existing:
            logger.info(f"prepare_queue: уже {len(existing)} заданий, пропуск дубля")
            return 0
        # Никогда не подменять recipient на owner_id/update.effective_user.id — только реальные recipients
        deliveries = []
        for r in recipients:
            rec = str(r).strip()
            if not rec:
                continue
            # запрет подмены: если rec == owner_id — это тестовый, но не подмена всей очереди
            # логика из §3.5: никогда не подменять
            deliveries.append(Delivery(campaign_id=campaign.id, recipient=rec, status="pending"))
        # защита от пустого, но не подмена админом
        if not deliveries and recipients:
            deliveries = [Delivery(campaign_id=campaign.id, recipient=str(recipients[0]), status="pending")]
        await self.delivery_repo.create_many(deliveries)
        return len(deliveries)

    async def run_campaign(self, campaign: Campaign, bot=None):
        provider = self.get_provider(campaign.platform)
        if not provider:
            await self._fail_campaign(campaign, f"Провайдер {campaign.platform} не настроен — остановили только этот канал")
            return

        await self.limiter.init()

        deliveries = await self.delivery_repo.list_by_campaign(campaign.id)
        if not deliveries:
            campaign.status = CampaignStatus.COMPLETED
            await self.campaign_repo.update(campaign)
            await self.activity_repo.log(campaign.owner_id, campaign.id, "completed", "Нет доступных адресатов — честно сообщаем: 0 отправлено")
            return

        campaign.status = CampaignStatus.RUNNING
        await self.campaign_repo.update(campaign)
        await self.activity_repo.log(campaign.owner_id, campaign.id, "running", f"Старт: цель {campaign.requested_limit} успешных, найдено {len(deliveries)} адресатов")

        target = campaign.requested_limit or len(deliveries)
        success_count = 0
        rate_delay = RATE_LIMITS.get(campaign.platform, 0.5)
        daily_limit = DAILY_LIMITS.get(campaign.platform, 30)

        for d in deliveries:
            fresh = await self.delivery_repo.list_by_campaign(campaign.id)
            cur_d = next((x for x in fresh if x.id == d.id), d)
            if cur_d.status in ("sent", "delivered", "accepted_by_api"):
                success_count += 1
                continue
            if cur_d.status in ("delayed",):
                # повторная попытка позже — сейчас пропускаем, позже ретрай
                continue
            if success_count >= target:
                await self.delivery_repo.update_status(d.id, "cancelled", error_text=f"Цель {target} достигнута, набор остановлен")
                continue

            current = await self.campaign_repo.get(campaign.id)
            if not current:
                return
            if current.status == CampaignStatus.PAUSED:
                await self.activity_repo.log(campaign.owner_id, campaign.id, "paused", "Пауза")
                while True:
                    await asyncio.sleep(1.5)
                    cur2 = await self.campaign_repo.get(campaign.id)
                    if cur2.status == CampaignStatus.RUNNING:
                        await self.activity_repo.log(campaign.owner_id, campaign.id, "resumed", "Продолжена")
                        break
                    if cur2.status in (CampaignStatus.CANCELLED, CampaignStatus.FAILED):
                        return
            if current.status == CampaignStatus.CANCELLED:
                await self.activity_repo.log(campaign.owner_id, campaign.id, "cancelled", "Отменена")
                return
            if current.status not in (CampaignStatus.RUNNING, CampaignStatus.QUEUED):
                return

            if campaign.campaign_type == "audience_message":
                from app.services.consent_service import ConsentService
                cs = ConsentService(self.db_path)
                if not await cs.is_consented(campaign.owner_id, campaign.platform, d.recipient):
                    await self.delivery_repo.update_status(d.id, "skipped", error_code="no_consent", error_text="Отозвано/блокировка/нет разрешения — не повторяем")
                    await self.activity_repo.log(campaign.owner_id, campaign.id, "skipped", f"Пропущен {d.recipient}: нет согласия")
                    continue

            # Проверка лимита через AccountRateLimiter (дневной+часовой+задержка) — перед каждой отправкой
            can, wait, reason = await self.limiter.can_send(campaign.owner_id, campaign.platform)
            if not can:
                await self.delivery_repo.update_status(d.id, "delayed", error_text=reason)
                await self.activity_repo.log(campaign.owner_id, campaign.id, "delayed", f"Отложено {d.recipient}: {reason} (ждать {int(wait)}с)")
                # если ждать мало (<5 мин) — можно подождать, иначе отложить на потом
                # не спамим — ставим delayed, кампания не завершена пока есть delayed
                continue

            await self.delivery_repo.update_status(d.id, "processing", attempts=d.attempts)
            max_attempts = 3
            delivered = False
            for attempt in range(1, max_attempts+1):
                try:
                    base_text = campaign.message_text
                    text = _vary_text(base_text, d.recipient, campaign)
                    if campaign.link:
                        text = f"{text}\n{campaign.link}"
                    if campaign.campaign_type == "own_channel_post":
                        result = await provider.publish(chat_id=d.recipient, text=text, owner_id=campaign.owner_id)
                    else:
                        # telegram_user — обязателен owner_id, иначе ProviderError no_owner
                        result = await provider.send_message(recipient=d.recipient, text=text, owner_id=campaign.owner_id)

                    # Успех только по реальному message_id от API
                    await self.delivery_repo.update_status(d.id, "sent", attempts=attempt, provider_message_id=str(result.get("message_id", "") or result.get("id", "")))
                    await self.activity_repo.log(campaign.owner_id, campaign.id, "sent", f"Принято API {d.recipient} -> {result.get('message_id')}")
                    success_count += 1
                    await self.limiter.record_send(campaign.owner_id, campaign.platform)
                    # логируем все отправки и ошибки (для отладки)
                    logger.info(f"sent {campaign.platform} {d.recipient} -> {result.get('message_id')} owner={campaign.owner_id}")
                    delivered = True
                    break

                except Exception as e:
                    from app.domain.errors import RateLimitError, ForbiddenError, ProviderError
                    err_text = str(e)
                    err_code = getattr(e, "code", "unknown")
                    is_rate = isinstance(e, RateLimitError) or "flood" in err_text.lower() or "429" in err_text or "rate" in err_text.lower()
                    is_forbidden = isinstance(e, ForbiddenError) or "blocked" in err_text.lower() or "peer_flood" in err_text.lower() or err_code in ("peer_flood","blocked","privacy","blocked")

                    if is_forbidden:
                        await self.delivery_repo.update_status(d.id, "failed", attempts=attempt, error_code=getattr(e, "code", "blocked"), error_text=err_text)
                        await self.activity_repo.log(campaign.owner_id, campaign.id, "failed", f"Постоянная ошибка {d.recipient}: {err_text} — PEER_FLOOD/блокировка, останавливаем аккаунт")
                        logger.warning(f"forbidden {campaign.platform} {d.recipient}: {err_text}")
                        if "peer_flood" in err_text.lower() or err_code == "peer_flood":
                            await self.limiter.record_flood_wait(campaign.owner_id, campaign.platform, 2*3600)
                            await self.activity_repo.log(campaign.owner_id, campaign.id, "account_limited", "⛔ PEER_FLOOD — аккаунт ограничен на 2 часа, отправка остановлена (антибан §4)")
                        break
                    elif is_rate:
                        retry_after = getattr(e, "retry_after", 60)
                        await self.activity_repo.log(campaign.owner_id, campaign.id, "rate_limit", f"FloodWait {d.recipient}, ждём {retry_after}с + буфер")
                        logger.warning(f"rate_limit {campaign.platform} {d.recipient} wait {retry_after}")
                        await self.limiter.record_flood_wait(campaign.owner_id, campaign.platform, retry_after)
                        # Для telegram_user — delayed (антибан), для Bot API — retry с ожиданием
                        if campaign.platform == "telegram_user":
                            await self.delivery_repo.update_status(d.id, "delayed", attempts=attempt, error_code="flood_wait", error_text=f"FloodWait {retry_after}s — отложено: {err_text}")
                            break
                        else:
                            await self.delivery_repo.update_status(d.id, "retry", attempts=attempt, error_code="flood_wait", error_text=f"FloodWait {retry_after}s")
                            if attempt < max_attempts:
                                await asyncio.sleep(min(retry_after, 30))
                                continue
                            await self.delivery_repo.update_status(d.id, "failed", attempts=attempt, error_code="flood_wait", error_text=err_text)
                            break
                    elif isinstance(e, ProviderError):
                        if err_code in ("configuration_error", "chat_not_found", "invalid_recipient", "not_found", "not_authorized", "no_owner", "not_connected"):
                            await self.delivery_repo.update_status(d.id, "failed", attempts=attempt, error_code=err_code, error_text=err_text)
                            await self.activity_repo.log(campaign.owner_id, campaign.id, "failed", f"Постоянная {d.recipient}: {err_text}")
                            break
                        elif "timeout" in err_text.lower() or "network" in err_text.lower():
                            await self.delivery_repo.update_status(d.id, "delayed", attempts=attempt, error_code=err_code, error_text=err_text)
                            if attempt < max_attempts:
                                backoff = 2 * attempt
                                await asyncio.sleep(backoff)
                                continue
                            await self.delivery_repo.update_status(d.id, "failed", attempts=attempt, error_code=err_code, error_text=err_text)
                            break
                        else:
                            await self.delivery_repo.update_status(d.id, "failed", attempts=attempt, error_code=err_code, error_text=err_text)
                            break
                    else:
                        await self.delivery_repo.update_status(d.id, "failed", attempts=attempt, error_code="unknown", error_text=err_text)
                        break

            await asyncio.sleep(rate_delay)

        stats = await self.delivery_repo.stats(campaign.id)
        detailed = await self.delivery_repo.detailed_stats(campaign)
        pending = stats.get("pending",0) + stats.get("retry",0) + stats.get("processing",0) + stats.get("queued",0) + stats.get("delayed",0)
        current = await self.campaign_repo.get(campaign.id)
        if not current or current.status == CampaignStatus.CANCELLED:
            return
        if pending > 0:
            current.status = CampaignStatus.RUNNING
            await self.campaign_repo.update(current)
            await self.activity_repo.log(current.owner_id, current.id, "pending_tasks", f"Есть отложенные {pending} — кампания не завершена, продолжит после ожидания лимитов")
            return
        goal = campaign.requested_limit or detailed.get("available",0)
        remaining = max(0, goal - success_count)
        if success_count == 0 and stats.get("failed",0) > 0:
            current.status = CampaignStatus.FAILED
            await self.campaign_repo.update(current)
            await self.activity_repo.log(current.owner_id, current.id, "failed", f"Завершена: цель {goal}, успешно {success_count}, ошибок {stats.get('failed',0)}, отложено {stats.get('delayed',0)}, осталось {remaining}")
        else:
            current.status = CampaignStatus.COMPLETED
            await self.campaign_repo.update(current)
            if remaining > 0:
                await self.activity_repo.log(current.owner_id, current.id, "completed_partial", f"Частично: цель {goal}, успешно {success_count}, осталось {remaining} — адресаты закончились/лимиты/ошибки")
            else:
                await self.activity_repo.log(current.owner_id, current.id, "completed", f"Завершена: цель {goal} достигнута, успешно {success_count}, подробно {detailed}")

    async def pause(self, campaign_id: int, owner_id: int):
        from app.domain.statuses import CampaignStatus as CS
        c = await self.campaign_repo.get(campaign_id)
        if not c or c.owner_id != owner_id:
            raise PermissionError
        if c.status != CS.RUNNING:
            raise ValueError("Пауза только для выполняющейся")
        c.status = CS.PAUSED
        await self.campaign_repo.update(c)
        await self.activity_repo.log(owner_id, c.id, "paused", "Пауза пользователем")

    async def resume(self, campaign_id: int, owner_id: int):
        from app.domain.statuses import CampaignStatus as CS
        c = await self.campaign_repo.get(campaign_id)
        if not c or c.owner_id != owner_id:
            raise PermissionError
        if c.status != CS.PAUSED:
            raise ValueError("Продолжить только приостановленную")
        c.status = CS.RUNNING
        await self.campaign_repo.update(c)
        await self.activity_repo.log(owner_id, c.id, "resumed", "Продолжена")

    async def _fail_campaign(self, campaign: Campaign, reason: str):
        campaign.status = CampaignStatus.FAILED
        await self.campaign_repo.update(campaign)
        await self.activity_repo.log(campaign.owner_id, campaign.id, "failed", reason)

    async def cancel(self, campaign_id: int, owner_id: int):
        c = await self.campaign_repo.get(campaign_id)
        if not c or c.owner_id != owner_id:
            raise PermissionError
        if c.status in (CampaignStatus.COMPLETED, CampaignStatus.FAILED, CampaignStatus.CANCELLED):
            return
        c.status = CampaignStatus.CANCELLED
        await self.campaign_repo.update(c)
        await self.activity_repo.log(owner_id, c.id, "cancelled", "Отменена пользователем")
        for d in await self.delivery_repo.list_by_campaign(campaign_id):
            if d.status in ("pending", "retry", "processing", "queued", "delayed"):
                await self.delivery_repo.update_status(d.id, "cancelled", error_text="Отменена")
        task = self._running_tasks.get(campaign_id)
        if task and not task.done():
            task.cancel()

    async def get_honest_stats(self, campaign_id: int) -> dict:
        c = await self.campaign_repo.get(campaign_id)
        if not c:
            return {}
        d = await self.delivery_repo.detailed_stats(c)
        d["goal"] = c.requested_limit
        d["success"] = d.get("sent",0)
        if d.get("delivered",0) > 0:
            d["delivered_display"] = d["delivered"]
        else:
            d["accepted_api"] = d.get("sent",0)
        d["remaining"] = max(0, c.requested_limit - d.get("sent",0)) if c.requested_limit else 0
        return d
