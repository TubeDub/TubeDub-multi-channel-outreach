import os
import httpx
from app.providers.base import BaseProvider
from app.domain.errors import ProviderError, RateLimitError

class MetaMessengerProvider(BaseProvider):
    platform = "facebook_messenger"

    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self.token = os.getenv("META_PAGE_ACCESS_TOKEN", "") or os.getenv("META_ACCESS_TOKEN", "")
        self.page_id = os.getenv("META_PAGE_ID", "")

    async def check_connection(self, owner_id: int = None) -> dict:
        if not self.token or not self.page_id:
            return {
                "status": "not_connected",
                "hint": "Нужны META_PAGE_ACCESS_TOKEN и META_PAGE_ID (создайте App в Meta for Developers → Messenger product → Generate Page token)",
                "capabilities": await self.get_capabilities(),
                "next_step": "Получите Page Access Token с правами pages_messaging, pages_manage_metadata → добавьте в .env → Мои аккаунты → Проверить",
                "required": ["META_PAGE_ACCESS_TOKEN","META_PAGE_ID"],
            }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"https://graph.facebook.com/v21.0/{self.page_id}",
                    params={"access_token": self.token, "fields": "name,id"}
                )
                data = resp.json()
                if "error" in data:
                    return {"status": "configuration_error", "hint": data["error"].get("message", "Ошибка токена"), "capabilities": await self.get_capabilities(), "next_step": self.next_step_hint("configuration_error")}
                # также проверим права через /me/permissions? но достаточно Page
                if self.db_path and owner_id:
                    try:
                        from app.storage.repositories import ProviderConnectionRepo
                        from app.domain.models import ProviderConnection
                        repo = ProviderConnectionRepo(self.db_path)
                        await repo.upsert(ProviderConnection(owner_id=owner_id, provider="facebook_messenger", status="connected", meta=f"Page {data.get('name')}"))
                    except:
                        pass
                return {"status": "connected", "hint": f"Page: {data.get('name')} ({data.get('id')}) — Messenger подключён, помните 24h окно", "capabilities": await self.get_capabilities(), "next_step": self.next_step_hint("connected")}
        except Exception as e:
            return {"status": "service_error", "hint": str(e), "capabilities": await self.get_capabilities(), "next_step": self.next_step_hint("service_error")}

    async def get_capabilities(self) -> dict:
        return {"send_message": True, "cold_outreach": False, "check_connection": True, "requires_page": True, "messaging_window": "24h"}

    async def send_message(self, recipient: str, text: str, owner_id: int = None) -> dict:
        if not self.token or not self.page_id:
            raise ProviderError("Messenger не подключён: нужен META_PAGE_ACCESS_TOKEN и META_PAGE_ID", code="not_connected")
        # recipient должен быть PSID, не личный профиль — честно проверяем
        if not recipient or len(recipient) < 5:
            raise ProviderError("Получатель должен быть PSID (Page-Scoped ID), полученный после сообщения пользователя в Page", code="invalid_recipient")
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"https://graph.facebook.com/v21.0/{self.page_id}/messages",
                params={"access_token": self.token},
                json={
                    "recipient": {"id": recipient},
                    "message": {"text": text},
                    "messaging_type": "RESPONSE"
                }
            )
            data = resp.json()
            if "error" in data:
                err = data["error"]
                msg = err.get("message","")
                if err.get("code") == 4 or "rate" in msg.lower():
                    raise RateLimitError(msg, code="rate_limit")
                if "outside" in msg.lower() and "window" in msg.lower():
                    raise ProviderError(f"Вне 24h окна: {msg} — используйте MESSAGE_TAG/One-Time Notification", code="outside_window")
                raise ProviderError(msg or "Ошибка отправки Messenger", code=str(err.get("code")))
            return {"message_id": data.get("message_id"), "recipient": recipient}

    async def publish(self, chat_id: str, text: str, owner_id: int = None) -> dict:
        raise ProviderError("Публикация в канал Messenger не поддерживается — только сообщения пользователям в окне", code="not_supported")

    async def validate_campaign(self, campaign) -> tuple[bool, list]:
        errs = []
        if campaign.platform != "facebook_messenger":
            errs.append("Кампания не для Messenger")
        errs.append("Требуется PSID получателей, obtidos после взаимодействия с Page — холодная рассылка личным профилям запрещена")
        return (False, errs)
