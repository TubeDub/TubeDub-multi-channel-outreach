from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.config import PAYMENT_MODE, SUBSCRIPTION_PRICE_USD, SUBSCRIPTION_PERIOD_DAYS, PAYMENT_CARD_NUMBER, PAYMENT_CARD_HOLDER, mask_card_number
from app.storage.repositories import PaymentRequestRepo, ActivityRepo
from app.domain.models import PaymentRequest

class PaymentProviderInterface:
    """Интерфейс для будущих платёжных провайдеров — создание, проверка, подтверждение"""
    async def create_payment(self, user_id: int, amount: float) -> Dict[str, Any]:
        raise NotImplementedError
    async def check_status(self, payment_id: str) -> Dict[str, Any]:
        raise NotImplementedError
    async def handle_confirmed(self, payment_id: str) -> bool:
        raise NotImplementedError

class ManualPlaceholderProvider(PaymentProviderInterface):
    """Заглушка — ручное подтверждение админом"""
    async def create_payment(self, user_id: int, amount: float) -> Dict[str, Any]:
        return {"mode": "manual_placeholder", "amount": amount, "note": "Ручное подтверждение админом"}
    async def check_status(self, payment_id: str) -> Dict[str, Any]:
        return {"status": "pending", "mode": "manual_placeholder"}
    async def handle_confirmed(self, payment_id: str) -> bool:
        return False

class PaymentService:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.repo = PaymentRequestRepo(db_path)
        self.activity = ActivityRepo(db_path)
        self.provider = ManualPlaceholderProvider()

    def get_config(self) -> Dict[str, Any]:
        return {
            "mode": PAYMENT_MODE,
            "price": SUBSCRIPTION_PRICE_USD,
            "period_days": SUBSCRIPTION_PERIOD_DAYS,
            "card_number": PAYMENT_CARD_NUMBER,
            "card_holder": PAYMENT_CARD_HOLDER,
            "card_masked": mask_card_number(PAYMENT_CARD_NUMBER) if PAYMENT_CARD_NUMBER else "",
            "is_configured": bool(PAYMENT_CARD_NUMBER),
        }

    async def create_request(self, user_id: int) -> tuple[bool, str, Optional[PaymentRequest]]:
        # защита от дублей: если уже есть pending — не создавать новую
        if await self.repo.has_pending(user_id):
            return False, "У вас уже есть заявка на рассмотрении. Дождитесь подтверждения администратора.", None
        cfg = self.get_config()
        if not cfg["is_configured"] and cfg["mode"] == "manual_placeholder":
            # всё равно создаём заявку, но предупредим что реквизиты не настроены
            pass
        pr = PaymentRequest(
            user_id=user_id,
            status="pending",
            amount_usd=cfg["price"],
            period_days=cfg["period_days"],
            payment_mode=cfg["mode"],
            card_last4=mask_card_number(cfg["card_number"]) if cfg["card_number"] else "",
            details=f"Заявка на подписку ${cfg['price']} на {cfg['period_days']} дней"
        )
        created = await self.repo.create(pr)
        await self.activity.log(user_id, None, "payment_request_created", f"Заявка #{created.id} ${created.amount_usd} pending")
        return True, "Заявка создана", created

    async def list_pending(self):
        return await self.repo.list_pending()

    async def approve(self, request_id: int, admin_id: int) -> tuple[bool, str]:
        pr = await self.repo.get(request_id)
        if not pr:
            return False, "Заявка не найдена"
        if pr.status != "pending":
            return False, f"Заявка уже {pr.status}"
        # проверка админа
        from app.config import is_admin
        if not is_admin(admin_id):
            return False, "Только администратор может подтверждать оплату"
        await self.repo.update_status(request_id, "approved", admin_id, "Одобрено администратором")
        # выдать подписку
        from app.services.subscription_service import SubscriptionService
        sub = SubscriptionService(self.db_path)
        await sub.grant_subscription(pr.user_id, pr.period_days, admin_id)
        await self.activity.log(admin_id, None, "payment_approved", f"Заявка #{request_id} approved для {pr.user_id}")
        await self.activity.log(pr.user_id, None, "subscription_activated", f"Подписка {pr.period_days} дней по заявке #{request_id}")
        return True, f"Подписка для {pr.user_id} активирована на {pr.period_days} дней"

    async def reject(self, request_id: int, admin_id: int, reason: str = "") -> tuple[bool, str]:
        pr = await self.repo.get(request_id)
        if not pr:
            return False, "Заявка не найдена"
        if pr.status != "pending":
            return False, f"Заявка уже {pr.status}"
        from app.config import is_admin
        if not is_admin(admin_id):
            return False, "Только администратор может отклонять"
        await self.repo.update_status(request_id, "rejected", admin_id, reason or "Отклонено")
        await self.activity.log(admin_id, None, "payment_rejected", f"Заявка #{request_id} rejected")
        return True, "Заявка отклонена"

    def format_offer(self) -> str:
        cfg = self.get_config()
        if not cfg["is_configured"]:
            return (
                f"💳 <b>Оформление подписки — ${cfg['price']}/мес</b>\n\n"
                f"⚠️ <b>Оплата пока настраивается. Попробуйте позже.</b>\n"
                f"Реквизиты ещё не заданы администратором.\n"
                f"Свяжитесь с поддержкой.\n"
            )
        return (
            f"💳 <b>Оформление подписки — ${cfg['price']} / {cfg['period_days']} дней</b>\n\n"
            f"Реквизиты для оплаты:\n"
            f"Карта: <code>{cfg['card_masked']}</code>\n"
            f"Получатель: {cfg['card_holder'] or '—'}\n"
            f"Режим: {cfg['mode']}\n\n"
            f"ℹ️ Автоматическое списание пока не реализовано.\n"
            f"После оплаты нажмите «✅ Я оплатил» — заявка уйдёт администратору.\n"
            f"Администратор вручную проверит и активирует подписку на 30 дней.\n"
        )

    def format_subscription_end_screen(self, free_used: int, free_total: int) -> str:
        cfg = self.get_config()
        return (
            f"🔒 <b>Бесплатный период завершён</b>\n\n"
            f"Вы использовали <b>{free_used}/{free_total}</b> бесплатных рассылок.\n"
            f"Оформите подписку, чтобы продолжить работу со всеми подключёнными каналами.\n\n"
            f"💎 Стоимость: <b>${cfg['price']} / месяц</b> ({cfg['period_days']} дней)\n"
            f"Включает все каналы, историю и экспорт данных.\n"
        )
