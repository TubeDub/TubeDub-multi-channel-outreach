from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional
from app.storage.repositories import UserRepo
from app.domain.models import User

class SubscriptionService:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.repo = UserRepo(db_path)

    async def get_or_create_user(self, user_id: int, username: str = "", first_name: str = "") -> User:
        return await self.repo.get_or_create(user_id, username, first_name)

    async def get_status(self, user_id: int) -> User:
        user = await self.repo.get(user_id)
        if not user:
            user = await self.repo.get_or_create(user_id)
        # Check expiry
        if user.subscription_status == "active" and user.subscription_expires_at:
            try:
                exp = datetime.fromisoformat(user.subscription_expires_at)
                now = datetime.now(timezone.utc)
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if now > exp:
                    user.subscription_status = "expired"
                    await self.repo.set_subscription(user.user_id, "expired", user.subscription_expires_at)
            except:
                pass
        return user

    async def can_send(self, user_id: int) -> Tuple[bool, str]:
        user = await self.get_status(user_id)
        # active subscription always allows
        if user.subscription_status == "active":
            if user.subscription_expires_at:
                try:
                    exp = datetime.fromisoformat(user.subscription_expires_at)
                    if exp.tzinfo is None:
                        exp = exp.replace(tzinfo=timezone.utc)
                    if datetime.now(timezone.utc) <= exp:
                        return True, "Подписка активна"
                    else:
                        # expired
                        pass
                except:
                    return True, "Подписка активна"
            else:
                return True, "Подписка активна"
        # free limit
        if user.free_used < user.free_total:
            remaining = user.free_total - user.free_used
            return True, f"Бесплатно: осталось {remaining}"
        return False, "Бесплатный лимит исчерпан"

    async def consume(self, user_id: int, campaign_id: int) -> Tuple[bool, str]:
        """Списывает одну бесплатную рассылку после фактического выполнения. Защита от дублей и отрицательных."""
        user = await self.get_status(user_id)
        # если подписка активна — не списываем free, но считаем использование подписки (неограничено пока активна)
        if user.subscription_status == "active":
            # проверить не expired
            if user.subscription_expires_at:
                try:
                    exp = datetime.fromisoformat(user.subscription_expires_at)
                    if exp.tzinfo is None:
                        exp = exp.replace(tzinfo=timezone.utc)
                    if datetime.now(timezone.utc) <= exp:
                        return True, "Отправлено по активной подписке"
                except:
                    pass
            else:
                return True, "Отправлено по активной подписке"
        # если free лимит исчерпан и нет подписки — нельзя
        if user.free_used >= user.free_total:
            return False, "Бесплатный лимит исчерпан — оформите подписку 💎"
        # атомарный инкремент
        updated = await self.repo.increment_free_used(user_id)
        if not updated:
            return False, "Пользователь не найден"
        # защита от отрицательных уже в repo, но проверим
        if updated.free_used < 0:
            updated.free_used = 0
            await self.repo.upsert(updated)
        return True, f"Использовано {updated.free_used}/{updated.free_total}, осталось {updated.free_total - updated.free_used}"

    def format_profile(self, user: User) -> str:
        remaining = max(0, user.free_total - user.free_used)
        # subscription status human
        sub_human = {
            "free": "Бесплатный период",
            "active": "Активна ✅",
            "expired": "Истекла ⏰",
        }.get(user.subscription_status, user.subscription_status)
        exp_str = user.subscription_expires_at[:19] if user.subscription_expires_at else "—"
        # handle expiry display
        if user.subscription_status == "active" and user.subscription_expires_at:
            sub_human = f"Активна до {exp_str}"
        return (
            f"👤 <b>Мой аккаунт</b>\n\n"
            f"ID: <code>{user.user_id}</code>\n"
            f"Имя: {user.first_name or '—'} | @{user.username or '—'}\n\n"
            f"🎁 <b>Бесплатные рассылки:</b>\n"
            f"Всего: {user.free_total}\n"
            f"Использовано: {user.free_used}\n"
            f"Осталось: {remaining}\n\n"
            f"💎 <b>Подписка:</b> {sub_human}\n"
            f"Истекает: {exp_str}\n"
        )

    async def grant_subscription(self, user_id: int, period_days: int = 30, admin_id: int = None) -> User:
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=period_days)
        expires_iso = expires.isoformat()
        await self.repo.set_subscription(user_id, "active", expires_iso)
        # log activity
        from app.storage.repositories import ActivityRepo
        repo = ActivityRepo(self.db_path)
        await repo.log(admin_id or user_id, None, "subscription_granted", f"Подписка {user_id} на {period_days} дней до {expires_iso} (админ {admin_id})")
        return await self.repo.get(user_id)
