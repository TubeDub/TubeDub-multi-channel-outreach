from abc import ABC, abstractmethod
from typing import Dict, Any

# Единый набор статусов подключения
STATUSES = ["connected", "not_connected", "configuration_error", "permission_error", "service_error"]

class BaseProvider(ABC):
    platform: str = "base"

    @abstractmethod
    async def check_connection(self, owner_id: int) -> Dict[str, Any]:
        """Return {status: connected|not_connected|configuration_error|permission_error|service_error, hint, capabilities, next_step}"""
        pass

    @abstractmethod
    async def get_capabilities(self) -> Dict[str, bool]:
        pass

    async def validate_campaign(self, campaign) -> tuple[bool, list]:
        return True, []

    async def send_message(self, recipient: str, text: str, owner_id: int = None) -> Dict[str, Any]:
        raise NotImplementedError(f"{self.platform} send_message not supported")

    async def publish(self, chat_id: str, text: str, owner_id: int = None) -> Dict[str, Any]:
        raise NotImplementedError(f"{self.platform} publish not supported")

    async def send_test(self, owner_id: int, target: str, text: str) -> Dict[str, Any]:
        return await self.send_message(target, text, owner_id)

    async def get_default_channel(self, owner_id: int) -> str | None:
        return None

    def status_explanation(self, status: str) -> str:
        mapping = {
            "connected": "Подключён и готов",
            "not_connected": "Не подключён — требуется настройка",
            "configuration_error": "Ошибка конфигурации — проверьте токен/настройки",
            "permission_error": "Нет разрешений — выдайте права в кабинете сервиса",
            "service_error": "Сервис временно недоступен",
        }
        return mapping.get(status, status)

    def status_emoji(self, status: str) -> str:
        return {
            "connected": "✅",
            "not_connected": "⚪",
            "configuration_error": "🟡",
            "permission_error": "🟠",
            "service_error": "🔴",
        }.get(status, "•")

    def next_step_hint(self, status: str) -> str:
        hints = {
            "connected": "Готов к отправке",
            "not_connected": "Добавьте токен в .env и перезапустите",
            "configuration_error": "Проверьте токен и перезапустите бота",
            "permission_error": "Выдайте разрешения в кабинете сервиса",
            "service_error": "Попробуйте позже",
        }
        return hints.get(status, "")
