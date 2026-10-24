import os
import httpx
from app.providers.base import BaseProvider
from app.domain.errors import ProviderError, RateLimitError

class InstagramProvider(BaseProvider):
    platform = "instagram"

    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self.token = os.getenv("META_PAGE_ACCESS_TOKEN", "") or os.getenv("META_ACCESS_TOKEN", "")
        self.page_id = os.getenv("META_PAGE_ID", "")
        self.ig_user_id = os.getenv("INSTAGRAM_USER_ID", "")

    async def check_connection(self, owner_id: int = None) -> dict:
        if not self.token:
            return {
                "status": "not_connected",
                "hint": "Нужен META_PAGE_ACCESS_TOKEN и Instagram Professional (Business/Creator) привязанный к Page",
                "capabilities": await self.get_capabilities(),
                "next_step": "Переведите Instagram в Professional → привяжите к Page → Meta App с instagram_manage_messages → token → .env",
                "required": ["INSTAGRAM_PROFESSIONAL","instagram_manage_messages"],
            }
        # проверяем через Graph API если есть page_id
        if not self.page_id:
            return {"status": "configuration_error", "hint": "Токен есть, но нужен META_PAGE_ID привязанного Page", "capabilities": await self.get_capabilities(), "next_step": self.next_step_hint("configuration_error")}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"https://graph.facebook.com/v21.0/{self.page_id}", params={"access_token": self.token, "fields": "connected_instagram_account"})
                data = resp.json()
                if "error" in data:
                    return {"status": "permission_error", "hint": data["error"].get("message"), "capabilities": await self.get_capabilities(), "next_step": self.next_step_hint("permission_error")}
                ig = data.get("connected_instagram_account")
                if not ig:
                    return {"status": "permission_error", "hint": "Page не связан с Instagram Professional — привяжите в Page Settings", "capabilities": await self.get_capabilities(), "next_step": self.next_step_hint("permission_error")}
                return {"status": "connected", "hint": f"Instagram Professional @{ig.get('id')} подключён — холодная рассылка личным запрещена, 24h окно", "capabilities": await self.get_capabilities(), "next_step": self.next_step_hint("connected")}
        except Exception as e:
            return {"status": "service_error", "hint": str(e), "capabilities": await self.get_capabilities(), "next_step": self.next_step_hint("service_error")}

    async def get_capabilities(self) -> dict:
        return {"send_message": True, "cold_outreach": False, "check_connection": True, "requires_professional": True}

    async def send_message(self, recipient: str, text: str, owner_id: int = None) -> dict:
        if not self.token or not self.page_id:
            raise ProviderError("Instagram не подключён: нужен Professional аккаунт и Page token", code="not_connected")
        # recipient — IGSID, полученный после сообщения пользователя
        if not recipient:
            raise ProviderError("Получатель должен быть Instagram-scoped ID (IGSID) после взаимодействия", code="invalid_recipient")
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"https://graph.facebook.com/v21.0/{self.page_id}/messages",
                params={"access_token": self.token},
                json={"recipient": {"id": recipient}, "message": {"text": text}, "messaging_type": "RESPONSE"}
            )
            data = resp.json()
            if "error" in data:
                err = data["error"]
                if err.get("code")==4:
                    raise RateLimitError(err.get("message"), code="rate_limit")
                raise ProviderError(err.get("message","Ошибка Instagram"), code=str(err.get("code")))
            return {"message_id": data.get("message_id"), "recipient": recipient}
