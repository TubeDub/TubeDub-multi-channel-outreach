from app.providers.base import BaseProvider
from app.domain.errors import ProviderError

class TikTokProvider(BaseProvider):
    platform = "tiktok"

    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self.token = ""

    async def check_connection(self, owner_id: int = None) -> dict:
        return {
            "status": "not_connected",
            "hint": "Массовая отправка DM через официальный API TikTok не поддерживается (требует партнёрского доступа Business Messaging API)",
            "capabilities": await self.get_capabilities(),
            "next_step": "TikTok: Недоступно для холодных рассылок — используйте другие каналы. Подробнее developers.tiktok.com",
            "available": False,
        }

    async def get_capabilities(self) -> dict:
        return {"send_message": False, "cold_outreach": False, "check_connection": True, "available": False, "business_messaging_limited": True}

    async def send_message(self, recipient: str, text: str, owner_id: int = None) -> dict:
        raise ProviderError("Массовая отправка DM через официальный API TikTok не поддерживается. Требует партнёрского доступа Business Messaging API — честно не обещаем.", code="not_supported")

    async def validate_campaign(self, campaign) -> tuple[bool, list]:
        return (False, ["TikTok холодные рассылки официально не поддерживаются — используйте Telegram/Email/WhatsApp"])
