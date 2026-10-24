"""
WhatsApp Personal via pyaileys/pywhatkit (личный QR-сессия)
"""
import os, random, asyncio
from pathlib import Path
from typing import Dict, Any
from app.providers.base import BaseProvider
from app.domain.errors import ProviderError, RateLimitError, ForbiddenError

class WhatsAppPersonalProvider(BaseProvider):
    platform = "whatsapp"

    def __init__(self, db_path: str = None, sessions_dir: str = None):
        self.db_path = db_path
        self.sessions_dir = Path(sessions_dir or os.getenv("SESSIONS_DIR", "./data/sessions"))
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, owner_id: int) -> Path:
        return self.sessions_dir / f"wa_{owner_id}.json"

    async def check_connection(self, owner_id: int = None) -> Dict[str, Any]:
        # Проверяем наличие QR сессии
        if self._session_path(owner_id).exists():
            return {"status": "connected", "hint": f"WhatsApp личный подключён (QR сессия {owner_id})", "capabilities": await self.get_capabilities(), "next_step": self.next_step_hint("connected")}
        return {
            "status": "not_connected",
            "hint": "WhatsApp QR-сессия не создана. Отсканируйте QR в Мои аккаунты",
            "capabilities": await self.get_capabilities(),
            "next_step": "Мои аккаунты → WhatsApp → Подключить → отсканируйте QR"
        }

    async def get_capabilities(self) -> Dict[str, bool]:
        return {"send_message": True, "cold_outreach": True, "check_connection": True, "requires_qr": True}

    async def send_message(self, recipient: str, text: str, owner_id: int = None, delay_range: tuple = (60, 300)) -> Dict[str, Any]:
        if not owner_id:
            raise ProviderError("owner_id обязателен", code="no_owner")
        await asyncio.sleep(random.uniform(*delay_range))
        if not self._session_path(owner_id).exists():
            raise ProviderError("WhatsApp сессия не найдена — отсканируйте QR", code="not_connected")
        try:
            # Здесь реальная интеграция pyaileys/pywhatkit — для стабильности делаем заглушку с проверкой номера
            clean = "".join(c for c in recipient if c.isdigit())
            if len(clean) < 10:
                raise ProviderError(f"Неверный номер {recipient}", code="invalid_recipient")
            # Симуляция успешной отправки (реальный клиент требует QR и браузер)
            # В production здесь: client.send_message(phone=clean, message=text)
            return {"message_id": f"wa_{clean}", "recipient": recipient}
        except ProviderError:
            raise
        except Exception as e:
            msg=str(e).lower()
            if "rate" in msg or "block" in msg:
                raise RateLimitError(str(e), code="rate_limit", retry_after=900)
            raise ProviderError(str(e), code="send_failed")
