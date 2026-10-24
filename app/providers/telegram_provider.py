import httpx
import os
from typing import Dict, Any
from app.providers.base import BaseProvider
from app.domain.errors import ProviderError, RateLimitError, ForbiddenError
from app.config import TELEGRAM_BOT_TOKEN

class TelegramProvider(BaseProvider):
    platform = "telegram"

    def __init__(self, token: str = None, db_path: str = None):
        self.token = token or TELEGRAM_BOT_TOKEN or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.db_path = db_path
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else ""

    async def check_connection(self, owner_id: int = None) -> Dict[str, Any]:
        if not self.token:
            return {"status": "not_connected", "hint": "TELEGRAM_BOT_TOKEN не настроен. Добавьте токен в .env", "capabilities": await self.get_capabilities(), "next_step": self.next_step_hint("not_connected")}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.base_url}/getMe")
                data = resp.json()
                if data.get("ok"):
                    bot_info = data.get("result", {})
                    if self.db_path and owner_id:
                        try:
                            from app.storage.repositories import ProviderConnectionRepo
                            from app.domain.models import ProviderConnection
                            repo = ProviderConnectionRepo(self.db_path)
                            await repo.upsert(ProviderConnection(owner_id=owner_id, provider="telegram", status="connected", meta=f"@{bot_info.get('username','')} | {bot_info.get('first_name','')}"))
                        except Exception:
                            pass
                    return {
                        "status": "connected",
                        "hint": f"Бот @{bot_info.get('username')} ({bot_info.get('first_name')}) — токен действителен",
                        "bot": bot_info,
                        "capabilities": await self.get_capabilities(),
                        "next_step": self.next_step_hint("connected")
                    }
                else:
                    err = data.get("description", "Unknown error")
                    code = data.get("error_code", 0)
                    if code == 401:
                        status = "permission_error"
                    elif "not found" in err.lower() or "unauthorized" in err.lower():
                        status = "configuration_error"
                    else:
                        status = "configuration_error"
                    if self.db_path and owner_id:
                        try:
                            from app.storage.repositories import ProviderConnectionRepo
                            from app.domain.models import ProviderConnection
                            repo = ProviderConnectionRepo(self.db_path)
                            await repo.upsert(ProviderConnection(owner_id=owner_id, provider="telegram", status=status, meta=err))
                        except Exception:
                            pass
                    return {"status": status, "hint": f"Ошибка проверки токена: {err}", "capabilities": await self.get_capabilities(), "next_step": self.next_step_hint(status)}
        except Exception as e:
            return {"status": "service_error", "hint": f"Сеть недоступна: {e}", "capabilities": await self.get_capabilities(), "next_step": self.next_step_hint("service_error")}

    async def get_capabilities(self) -> Dict[str, bool]:
        return {
            "send_message": True,
            "publish_to_channel": True,
            "check_connection": True,
            "get_status": True,
            "audience_geo_search": False,
        }

    async def validate_campaign(self, campaign) -> tuple[bool, list]:
        errs = []
        if campaign.platform != "telegram":
            errs.append("Кампания не для Telegram")
        if campaign.campaign_type == "ads_campaign":
            errs.append("Рекламные кампании Telegram требуют отдельного Ads API — пока не реализовано")
        return (len(errs)==0, errs)

    async def send_message(self, recipient: str, text: str, owner_id: int = None) -> Dict[str, Any]:
        if not self.token:
            raise ProviderError("Telegram token не настроен", code="configuration_error")
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(f"{self.base_url}/sendMessage", json={"chat_id": recipient, "text": text})
            data = resp.json()
            if data.get("ok"):
                return {"message_id": data["result"]["message_id"], "chat_id": recipient}
            else:
                desc = data.get("description", "Unknown")
                code = data.get("error_code", 400)
                if code == 429:
                    params = data.get("parameters", {})
                    retry_after = params.get("retry_after", 5)
                    raise RateLimitError(desc, code=str(code), retry_after=retry_after)
                if code == 403:
                    raise ForbiddenError(desc, code=str(code))
                if "chat not found" in desc.lower() or "bad request" in desc.lower():
                    raise ProviderError(desc, code="configuration_error")
                raise ProviderError(desc, code=str(code))

    async def publish(self, chat_id: str, text: str, owner_id: int = None) -> Dict[str, Any]:
        if not self.token:
            raise ProviderError("Telegram token не настроен", code="configuration_error")
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.base_url}/getChat", params={"chat_id": chat_id})
                data = resp.json()
                if not data.get("ok"):
                    desc = data.get("description","")
                    if "chat not found" in desc.lower():
                        raise ProviderError(f"Канал/чат {chat_id} не найден. Убедитесь, что бот добавлен в канал как администратор.", code="chat_not_found")
        except ProviderError:
            raise
        except Exception:
            pass
        return await self.send_message(chat_id, text, owner_id)

    async def get_default_channel(self, owner_id: int) -> str | None:
        if not self.db_path:
            return None
        try:
            from app.storage.repositories import ProviderConnectionRepo
            repo = ProviderConnectionRepo(self.db_path)
            pc2 = await repo.get(owner_id, "telegram_channel")
            if pc2 and pc2.meta:
                return pc2.meta
        except Exception:
            pass
        return None

    async def set_default_channel(self, owner_id: int, channel_id: str):
        if not self.db_path:
            return
        from app.storage.repositories import ProviderConnectionRepo
        from app.domain.models import ProviderConnection
        repo = ProviderConnectionRepo(self.db_path)
        await repo.upsert(ProviderConnection(owner_id=owner_id, provider="telegram_channel", status="connected", meta=channel_id))
