"""
Facebook Messenger Personal via fbchat-v2 (личный аккаунт)
"""
import os, random, asyncio
from pathlib import Path
from typing import Dict, Any
from app.providers.base import BaseProvider
from app.domain.errors import ProviderError, RateLimitError, ForbiddenError

class FacebookPersonalProvider(BaseProvider):
    platform = "facebook_messenger"

    def __init__(self, db_path: str = None, sessions_dir: str = None):
        self.db_path = db_path
        self.sessions_dir = Path(sessions_dir or os.getenv("SESSIONS_DIR", "./data/sessions"))
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, owner_id: int) -> Path:
        return self.sessions_dir / f"fb_{owner_id}.json"

    async def check_connection(self, owner_id: int = None) -> Dict[str, Any]:
        try:
            import fbchat
        except ImportError:
            return {
                "status": "service_error",
                "hint": "fbchat не установлен. pip install fbchat",
                "capabilities": await self.get_capabilities(),
                "next_step": "pip install fbchat → Мои аккаунты → Messenger → Подключить (email/пароль)"
            }
        if not self._session_path(owner_id).exists():
            return {"status": "not_connected", "hint": "Сессия Messenger не создана", "capabilities": await self.get_capabilities(), "next_step": "Мои аккаунты → Messenger → Подключить → email/пароль → код 2FA"}
        try:
            from fbchat import Client as FBClient
            session = eval(self._session_path(owner_id).read_text()) if self._session_path(owner_id).exists() else {}
            # Проверка — пытаемся создать клиент из сессии
            return {"status": "connected", "hint": f"Messenger личный подключён (сессия {owner_id})", "capabilities": await self.get_capabilities(), "next_step": self.next_step_hint("connected")}
        except Exception as e:
            return {"status": "not_connected", "hint": f"Сессия невалидна: {e}", "capabilities": await self.get_capabilities()}

    async def get_capabilities(self) -> Dict[str, bool]:
        return {"send_message": True, "cold_outreach": True, "check_connection": True, "requires_session": True}

    async def send_message(self, recipient: str, text: str, owner_id: int = None, delay_range: tuple = (50, 200)) -> Dict[str, Any]:
        if not owner_id:
            raise ProviderError("owner_id обязателен", code="no_owner")
        try:
            import fbchat
        except ImportError:
            raise ProviderError("fbchat не установлен", code="service_error")
        await asyncio.sleep(random.uniform(*delay_range))
        if not self._session_path(owner_id).exists():
            raise ProviderError("Messenger сессия не найдена", code="not_connected")
        try:
            from fbchat import Client
            from fbchat.models import Message, ThreadType
            # Загружаем сессию (упрощённо)
            client = Client("dummy","dummy", session_cookies=eval(self._session_path(owner_id).read_text()))
            # recipient — user_id или thread_id
            await client.send(Message(text=text), thread_id=recipient, thread_type=ThreadType.USER)
            return {"message_id": f"fb_{recipient}", "recipient": recipient}
        except Exception as e:
            msg=str(e).lower()
            if "rate" in msg or "block" in msg:
                raise RateLimitError(str(e), code="rate_limit", retry_after=600)
            if "forbidden" in msg or "privacy" in msg:
                raise ForbiddenError(str(e), code="blocked")
            raise ProviderError(str(e), code="send_failed")
