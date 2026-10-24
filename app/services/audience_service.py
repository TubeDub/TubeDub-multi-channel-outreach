import json
from app.domain.models import Campaign
from app.services.consent_service import ConsentService

class AudienceService:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.consent = ConsentService(db_path)

    async def resolve_recipients(self, campaign: Campaign) -> list:
        """
        Resolve audience based on campaign.audience_source with strict consent checks.
        Приоритет: ручной список из recipients_json (шаг 3 мастера), иначе — по источнику.
        География сама по себе не создаёт получателей.
        """
        # 1. Ручной список (если пользователь ввёл получателей вручную)
        try:
            manual = json.loads(getattr(campaign, 'recipients_json', '[]') or '[]')
            if manual:
                # Для ручного списка тоже проверяем согласие, если применимо, но для Email manual — считаем согласие дано через импорт
                # Для строгости — вернём как есть, delivery_service проверит consent
                return manual
        except Exception:
            pass

        if campaign.audience_source == "bot_subscribers":
            contacts = await self.consent.get_audience(campaign.owner_id, campaign.platform)
            if campaign.requested_limit > 0:
                contacts = contacts[:campaign.requested_limit]
            return [c.external_id for c in contacts]
        elif campaign.audience_source == "own_channel":
            return []
        elif campaign.audience_source == "imported_list":
            contacts = await self.consent.get_audience(campaign.owner_id, campaign.platform)
            return [c.external_id for c in contacts]
        elif campaign.audience_source in ("inbound_leads", "ads_audience"):
            contacts = await self.consent.get_audience(campaign.owner_id, campaign.platform)
            return [c.external_id for c in contacts]
        else:
            return []

    def explain_audience(self, campaign: Campaign) -> str:
        if campaign.audience_source == "bot_subscribers":
            return "Подписчики бота — только те, кто сам начал диалог и не отписался (/stop)"
        elif campaign.audience_source == "own_channel":
            return "Публикация в ваш канал/страницу, где боту выданы права"
        elif campaign.audience_source == "imported_list":
            return "Импортированный список с подтверждённым согласием"
        elif campaign.audience_source == "inbound_leads":
            return "Лиды из официальной интеграции"
        elif campaign.audience_source == "ads_audience":
            return "Аудитория официальной рекламной платформы"
        return "Неизвестный источник"

    def geography_notice(self) -> str:
        return "⚠️ География — параметр таргетинга, а не список контактов. Приложение не ищет пользователей по городу и не пишет незнакомцам."
