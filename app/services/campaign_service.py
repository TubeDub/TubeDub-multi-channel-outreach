import uuid
from typing import Optional, List, Tuple
from app.domain.models import Campaign
from app.domain.statuses import CampaignStatus, can_transition
from app.domain.errors import NotFound, PermissionDenied, TransitionError, ValidationError
from app.storage.repositories import CampaignRepo, ActivityRepo
from app.services.validation_service import validate_campaign

class CampaignService:
    def __init__(self, db_path: str):
        self.repo = CampaignRepo(db_path)
        self.activity = ActivityRepo(db_path)
        self.db_path = db_path

    async def create_draft(self, campaign: Campaign) -> Campaign:
        is_valid, errors = validate_campaign(campaign)
        # allow creation even if not valid, but status will be needs_setup
        # For draft we allow incomplete but warn
        campaign.status = "draft"
        campaign.idempotency_key = str(uuid.uuid4())
        created = await self.repo.create(campaign)
        await self.activity.log(created.owner_id, created.id, "created", f"Создана кампания #{created.id} [{created.platform}]")
        # auto-determine status
        await self._recompute_status(created)
        return await self.repo.get(created.id)

    async def get_owned(self, campaign_id: int, owner_id: int) -> Campaign:
        c = await self.repo.get(campaign_id)
        if not c:
            raise NotFound(f"Кампания #{campaign_id} не найдена")
        if c.owner_id != owner_id:
            raise PermissionDenied("Нет доступа к этой кампании")
        return c

    async def update(self, campaign_id: int, owner_id: int, **fields) -> Campaign:
        c = await self.get_owned(campaign_id, owner_id)
        if c.status in ("queued", "running"):
            raise TransitionError("Нельзя редактировать кампанию в очереди/в процессе выполнения. Сначала отмените.")
        for k, v in fields.items():
            if hasattr(c, k):
                setattr(c, k, v)
        is_valid, errors = validate_campaign(c)
        if not is_valid:
            # still allow saving as draft/needs_setup but record
            pass
        updated = await self.repo.update(c)
        await self.activity.log(owner_id, c.id, "updated", f"Отредактирована кампания #{c.id}: {', '.join(fields.keys())}")
        await self._recompute_status(updated)
        return await self.repo.get(campaign_id)

    async def duplicate(self, campaign_id: int, owner_id: int) -> Campaign:
        orig = await self.get_owned(campaign_id, owner_id)
        copy = Campaign(
            owner_id=owner_id,
            platform=orig.platform,
            campaign_type=orig.campaign_type,
            country=orig.country,
            city=orig.city,
            audience_source=orig.audience_source,
            audience_mode=orig.audience_mode,
            requested_limit=orig.requested_limit,
            message_text=orig.message_text,
            link=orig.link,
            schedule_at=None,
            status="draft",
            idempotency_key=str(uuid.uuid4())
        )
        created = await self.repo.create(copy)
        await self.activity.log(owner_id, created.id, "duplicated", f"Скопирована из #{orig.id} в #{created.id}")
        return created

    async def delete(self, campaign_id: int, owner_id: int):
        c = await self.get_owned(campaign_id, owner_id)
        if c.status in ("queued", "running", "paused"):
            raise TransitionError("Нельзя удалить кампанию в процессе выполнения. Сначала отмените.")
        await self.repo.delete(campaign_id)
        await self.activity.log(owner_id, campaign_id, "deleted", f"Удалена кампания #{campaign_id}")

    async def set_status(self, campaign_id: int, owner_id: int, new_status: str, idempotency_key: str = None) -> Campaign:
        c = await self.get_owned(campaign_id, owner_id)
        if idempotency_key and c.idempotency_key == idempotency_key:
            # duplicate call protection: already in target state?
            if c.status == new_status:
                return c
        if not can_transition(c.status, new_status):
            raise TransitionError(f"Переход {c.status} -> {new_status} запрещён")
        c.status = new_status
        if idempotency_key:
            c.idempotency_key = idempotency_key
        updated = await self.repo.update(c)
        await self.activity.log(owner_id, c.id, f"status_{new_status}", f"Статус #{c.id}: {new_status}")
        return updated

    async def _recompute_status(self, c: Campaign):
        # Determine if ready or needs_setup based on validation
        is_valid, errors = validate_campaign(c)
        # check provider connection will be done in readiness check externally
        # Here we just keep draft/needs_setup logic
        if c.status == "draft":
            if is_valid:
                # keep draft until user explicitly queues; but we could mark ready
                pass
            else:
                c.status = "needs_setup"
                await self.repo.update(c)
                await self.activity.log(c.owner_id, c.id, "needs_setup", "; ".join(errors))

    async def check_readiness(self, campaign_id: int, owner_id: int, provider_checker) -> Tuple[bool, List[str]]:
        c = await self.get_owned(campaign_id, owner_id)
        reasons = []
        ok, errs = validate_campaign(c)
        if not ok:
            reasons.extend(errs)
        # provider check
        provider_status = await provider_checker(c.platform, owner_id)
        # provider_status is dict with status
        if provider_status.get("status") != "connected":
            reasons.append(f"Канал {c.platform} не подключён: {provider_status.get('status')} — {provider_status.get('hint','Проверьте Подключения')}")
        # audience source check
        if c.audience_source == "bot_subscribers":
            # need at least some consented contacts - but we allow 0 as "will be determined"
            pass
        # campaign_type vs platform rules
        if c.platform in ("facebook_messenger", "instagram", "whatsapp", "tiktok") and provider_status.get("status") != "connected":
            reasons.append(f"Для {c.platform} требуется подключить официальный API в разделе Подключения")

        if reasons:
            # set to needs_setup if not already final
            if c.status not in ("running", "queued", "paused", "completed", "failed", "cancelled"):
                c.status = "needs_setup"
                await self.repo.update(c)
            return False, reasons
        else:
            if c.status in ("draft", "needs_setup"):
                c.status = "ready"
                await self.repo.update(c)
                await self.activity.log(owner_id, c.id, "ready", "Кампания готова к запуску")
            return True, []

    async def list_paginated(self, owner_id: int, page: int = 1, per_page: int = 5) -> Tuple[List[Campaign], int, int]:
        total = await self.repo.count_by_owner(owner_id)
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        offset = (page - 1) * per_page
        items = await self.repo.list_by_owner(owner_id, limit=per_page, offset=offset)
        return items, total, total_pages
