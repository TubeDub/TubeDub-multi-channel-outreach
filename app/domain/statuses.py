from enum import Enum

class CampaignStatus(str, Enum):
    DRAFT = "draft"
    NEEDS_SETUP = "needs_setup"
    READY = "ready"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @classmethod
    def display(cls, status: str) -> str:
        mapping = {
            "draft": "Черновик",
            "needs_setup": "Требует настройки",
            "ready": "Готова к запуску",
            "queued": "В очереди",
            "running": "Выполняется",
            "paused": "Приостановлена",
            "completed": "Завершена",
            "failed": "Ошибка",
            "cancelled": "Отменена",
        }
        return mapping.get(status, status)

    @classmethod
    def emoji(cls, status: str) -> str:
        mapping = {
            "draft": "📝",
            "needs_setup": "⚠️",
            "ready": "✅",
            "queued": "⏳",
            "running": "🚀",
            "paused": "⏸",
            "completed": "🏁",
            "failed": "❌",
            "cancelled": "🛑",
        }
        return mapping.get(status, "•")

ALLOWED_TRANSITIONS = {
    "draft": {"needs_setup", "ready", "cancelled"},
    "needs_setup": {"draft", "ready", "cancelled"},
    "ready": {"queued", "draft", "cancelled"},
    "queued": {"running", "cancelled", "paused"},
    "running": {"completed", "failed", "paused", "cancelled"},
    "paused": {"running", "cancelled", "queued"},
    "completed": set(),
    "failed": {"ready", "draft", "queued"},
    "cancelled": {"draft", "ready"},
}

def can_transition(from_status: str, to_status: str) -> bool:
    return to_status in ALLOWED_TRANSITIONS.get(from_status, set())

class Platform(str, Enum):
    TELEGRAM = "telegram"
    TELEGRAM_USER = "telegram_user"
    FACEBOOK_MESSENGER = "facebook_messenger"
    INSTAGRAM = "instagram"
    WHATSAPP = "whatsapp"
    TIKTOK = "tiktok"
    EMAIL = "email"

    @classmethod
    def display(cls, platform: str) -> str:
        mapping = {
            "telegram": "Telegram Бот",
            "telegram_user": "Telegram Личный",
            "facebook_messenger": "Facebook Messenger",
            "instagram": "Instagram",
            "whatsapp": "WhatsApp",
            "tiktok": "TikTok",
            "email": "Email",
        }
        return mapping.get(platform, platform)

    @classmethod
    def all_values(cls):
        return [e.value for e in cls]

class CampaignType(str, Enum):
    OWN_CHANNEL_POST = "own_channel_post"
    AUDIENCE_MESSAGE = "audience_message"
    ADS_CAMPAIGN = "ads_campaign"

    @classmethod
    def display(cls, ct: str) -> str:
        m = {
            "own_channel_post": "Публикация в канал/страницу",
            "audience_message": "Сообщение аудитории",
            "ads_campaign": "Рекламная кампания",
        }
        return m.get(ct, ct)

class AudienceSource(str, Enum):
    OWN_CHANNEL = "own_channel"
    BOT_SUBSCRIBERS = "bot_subscribers"
    IMPORTED_LIST = "imported_list"
    INBOUND_LEADS = "inbound_leads"
    ADS_AUDIENCE = "ads_audience"

    @classmethod
    def display(cls, src: str) -> str:
        m = {
            "own_channel": "Собственный канал/страница",
            "bot_subscribers": "Подписчики бота",
            "imported_list": "Импортированный список",
            "inbound_leads": "Входящие лиды",
            "ads_audience": "Рекламная аудитория",
        }
        return m.get(src, src)

class AudienceMode(str, Enum):
    SUBSCRIBERS = "subscribers"
    LEADS = "leads"
    BOTH = "both"

    @classmethod
    def display(cls, mode: str) -> str:
        m = {"subscribers": "Подписчики", "leads": "Потенциальные клиенты", "both": "Обе категории"}
        return m.get(mode, mode)
