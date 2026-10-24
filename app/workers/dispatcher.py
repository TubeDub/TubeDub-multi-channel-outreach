import asyncio
import json
from app.storage.repositories import CampaignRepo, ActivityRepo
from app.domain.statuses import CampaignStatus
from app.observability.logging_config import get_logger

logger = get_logger(__name__)

class Dispatcher:
    def __init__(self, db_path: str, delivery_service):
        self.db_path = db_path
        self.delivery_service = delivery_service
        self.running = False

    async def dispatch_one(self, campaign_id: int, owner_id: int):
        repo = CampaignRepo(self.db_path)
        campaign = await repo.get(campaign_id)
        if not campaign:
            logger.warning(f"dispatch: campaign {campaign_id} not found")
            return
        if campaign.owner_id != owner_id:
            logger.warning("owner mismatch on dispatch")
            return
        # Идемпотентность: если уже completed — не дублируем списание
        if campaign.status in ("running", "completed"):
            logger.info(f"dispatch: campaign {campaign.id} already {campaign.status}, skipping duplicate")
            return
        # Проверка лимита перед подготовкой (дополнительно к проверке в handler)
        from app.services.subscription_service import SubscriptionService
        sub = SubscriptionService(self.db_path)
        can, msg = await sub.can_send(owner_id)
        if not can:
            # не ставим в очередь, помечаем needs_setup с причиной
            campaign.status = "needs_setup"
            await repo.update(campaign)
            act = ActivityRepo(self.db_path)
            await act.log(owner_id, campaign_id, "subscription_blocked", msg)
            logger.info(f"dispatch blocked by subscription: {msg}")
            return

        from app.services.audience_service import AudienceService
        aud = AudienceService(self.db_path)
        recipients = await aud.resolve_recipients(campaign)
        # Для публикаций — проверим канал, но queue всё равно
        if campaign.status != "queued":
            campaign.status = "queued"
            await repo.update(campaign)
        count = await self.delivery_service.prepare_queue(campaign, recipients)
        logger.info(f"Queued {count} deliveries for campaign {campaign.id}")
        task = asyncio.create_task(self.delivery_service.run_campaign(campaign))
        self.delivery_service._running_tasks[campaign.id] = task
        try:
            await task
        except asyncio.CancelledError:
            logger.info(f"Campaign {campaign.id} cancelled mid-run")
            return
        except Exception as e:
            logger.exception(f"Error running campaign {campaign.id}: {e}")
            return

        # После выполнения — списать одну рассылку, если завершена успешно
        final = await repo.get(campaign_id)
        if final and final.status == CampaignStatus.COMPLETED:
            # защита от повторного списания: проверим activity, была ли уже free_consumed для этой кампании
            act_repo = ActivityRepo(self.db_path)
            history = await act_repo.list_by_campaign(campaign_id)
            already = any(h.event == "free_consumed" for h in history)
            if not already:
                ok, msg_consume = await sub.consume(owner_id, campaign_id)
                await act_repo.log(owner_id, campaign_id, "free_consumed", msg_consume)
                logger.info(f"Free consumed for {owner_id}: {msg_consume}")
            else:
                logger.info(f"Already consumed for campaign {campaign_id}, skipping duplicate")
        elif final and final.status == CampaignStatus.FAILED:
            # Ошибки не списывают лимит (по ТЗ: ошибка подключения не расходует), но логируем
            act_repo = ActivityRepo(self.db_path)
            await act_repo.log(owner_id, campaign_id, "failed_no_charge", "Ошибка — бесплатная рассылка не списана")
