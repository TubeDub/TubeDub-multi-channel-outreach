import os
import httpx
from app.providers.base import BaseProvider
from app.domain.errors import ProviderError, RateLimitError

class WhatsAppProvider(BaseProvider):
    platform = "whatsapp"

    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self.token = os.getenv("WHATSAPP_TOKEN", "")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")

    async def check_connection(self, owner_id: int = None) -> dict:
        if not self.token or not self.phone_number_id:
            return {
                "status": "not_connected",
                "hint": "Нужны WHATSAPP_TOKEN и WHATSAPP_PHONE_NUMBER_ID (WhatsApp Cloud API → Meta for Developers → WhatsApp product)",
                "capabilities": await self.get_capabilities(),
                "next_step": "Создайте WhatsApp Business Account → Meta для Developers → Generate token → добавьте в .env → Business Verification для лимитов 250+",
                "required": ["WHATSAPP_TOKEN","WHATSAPP_PHONE_NUMBER_ID"],
            }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"https://graph.facebook.com/v21.0/{self.phone_number_id}",
                    params={"fields": "display_phone_number,verified_name", "access_token": self.token}
                )
                data = resp.json()
                if "error" in data:
                    return {"status": "configuration_error", "hint": data["error"].get("message","Ошибка токена"), "capabilities": await self.get_capabilities(), "next_step": self.next_step_hint("configuration_error")}
                name = data.get("verified_name") or data.get("display_phone_number")
                return {"status": "connected", "hint": f"WhatsApp Cloud API: {name} — помните шаблоны вне 24h окна, лимит 250/день старт", "capabilities": await self.get_capabilities(), "next_step": self.next_step_hint("connected")}
        except Exception as e:
            return {"status": "service_error", "hint": str(e), "capabilities": await self.get_capabilities(), "next_step": self.next_step_hint("service_error")}

    async def get_capabilities(self) -> dict:
        return {"send_message": True, "cold_outreach": False, "check_connection": True, "templates_required": True, "requires_business_verification": True}

    async def send_message(self, recipient: str, text: str, owner_id: int = None) -> dict:
        if not self.token or not self.phone_number_id:
            raise ProviderError("WhatsApp не подключён: WHATSAPP_TOKEN/PHONE_NUMBER_ID не заданы", code="not_connected")
        # recipient — номер в международном формате без +
        clean = "".join(c for c in recipient if c.isdigit())
        if len(clean) < 10:
            raise ProviderError(f"Неверный номер {recipient} — нужен международный формат", code="invalid_recipient")
        # Вне 24h окна требуются утверждённые шаблоны — честно предупреждаем, но пробуем как текст (для тестов)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"https://graph.facebook.com/v21.0/{self.phone_number_id}/messages",
                headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
                json={
                    "messaging_product": "whatsapp",
                    "to": clean,
                    "type": "text",
                    "text": {"preview_url": False, "body": text}
                }
            )
            data = resp.json()
            if "error" in data:
                err = data["error"]
                if err.get("code") in (4,80007) or "rate" in err.get("message","").lower():
                    raise RateLimitError(err.get("message"), code="rate_limit")
                raise ProviderError(err.get("message","Ошибка WhatsApp"), code=str(err.get("code")))
            # успехом считается wamid
            msg = data.get("messages", [{}])[0]
            return {"message_id": msg.get("id"), "recipient": recipient}

    async def validate_campaign(self, campaign) -> tuple[bool, list]:
        errs = []
        if campaign.platform != "whatsapp":
            errs.append("Кампания не для WhatsApp")
        errs.append("Для массовых исходящих вне 24h требуются утверждённые шаблоны — подготовьте их в Business Manager")
        return (False, errs)
