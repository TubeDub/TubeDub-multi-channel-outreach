"""
Instagram Personal Provider via instagrapi (личный аккаунт)
НЕ Business API — прямой логин/сессия
"""
import os
import random
import asyncio
from pathlib import Path
from typing import Dict, Any
from app.providers.base import BaseProvider
from app.domain.errors import ProviderError, RateLimitError, ForbiddenError

class InstagramPersonalProvider(BaseProvider):
    platform = "instagram"

    def __init__(self, db_path: str = None, sessions_dir: str = None):
        self.db_path = db_path
        self.sessions_dir = Path(sessions_dir or os.getenv("SESSIONS_DIR", "./data/sessions"))
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._clients: Dict[int, Any] = {}

    def _session_path(self, owner_id: int) -> Path:
        return self.sessions_dir / f"instagram_{owner_id}.json"

    async def check_connection(self, owner_id: int = None) -> Dict[str, Any]:
        # Попытка реального импорта instagrapi
        try:
            import instagrapi
        except ImportError:
            return {
                "status": "service_error",
                "hint": "instagrapi не установлен. pip install instagrapi — затем подключите логин/пароль",
                "capabilities": await self.get_capabilities(),
                "next_step": "pip install instagrapi && Мои аккаунты → Instagram → Подключить (логин/пароль)"
            }
        if owner_id is None:
            return {"status": "not_connected", "hint": "owner_id обязателен", "capabilities": await self.get_capabilities()}
        # Проверяем сессию
        if not self._session_path(owner_id).exists():
            return {
                "status": "not_connected",
                "hint": "Сессия Instagram не создана. Подключите логин/пароль в Мои аккаунты",
                "capabilities": await self.get_capabilities(),
                "next_step": "Мои аккаунты → Instagram → Подключить → логин/пароль → 2FA если нужно"
            }
        try:
            from instagrapi import Client
            cl = Client()
            cl.load_settings(str(self._session_path(owner_id)))
            # лёгкая проверка без полного логина
            cl.get_timeline_feed()  # или account_info
            return {
                "status": "connected",
                "hint": f"Instagram личный @{cl.username} подключён",
                "capabilities": await self.get_capabilities(),
                "user": {"username": cl.username},
                "next_step": self.next_step_hint("connected")
            }
        except Exception as e:
            return {"status": "not_connected", "hint": f"Сессия невалидна: {e}", "capabilities": await self.get_capabilities(), "next_step": "Переподключите логин/пароль"}

    async def get_capabilities(self) -> Dict[str, bool]:
        return {"send_message": True, "cold_outreach": True, "check_connection": True, "requires_session": True}

    async def send_message(self, recipient: str, text: str, owner_id: int = None, delay_range: tuple = (60, 240)) -> Dict[str, Any]:
        if not owner_id:
            raise ProviderError("owner_id обязателен", code="no_owner")
        try:
            import instagrapi
        except ImportError:
            raise ProviderError("instagrapi не установлен — pip install instagrapi", code="service_error")
        await asyncio.sleep(random.uniform(*delay_range))
        if not self._session_path(owner_id).exists():
            raise ProviderError("Instagram сессия не найдена — подключите аккаунт", code="not_connected")
        try:
            from instagrapi import Client
            cl = Client()
            cl.load_settings(str(self._session_path(owner_id)))
            cl.login_by_sessionid(cl.sessionid)  # или просто ensure
            # recipient — username или user_id
            user_id = None
            if recipient.isdigit():
                user_id = recipient
            else:
                user_id = cl.user_id_from_username(recipient.lstrip("@"))
            # instagrapi direct_send
            thread_id = cl.direct_send(text, user_ids=[user_id])
            return {"message_id": str(thread_id), "recipient": recipient}
        except Exception as e:
            msg = str(e).lower()
            if "feedback" in msg or "rate" in msg or "wait" in msg:
                raise RateLimitError(str(e), code="rate_limit", retry_after=300)
            if "block" in msg or "challenge" in msg:
                raise ForbiddenError(str(e), code="blocked")
            raise ProviderError(str(e), code="send_failed")
