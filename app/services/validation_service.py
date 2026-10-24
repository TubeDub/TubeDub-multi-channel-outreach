from urllib.parse import urlparse
from app.domain.models import Campaign
from app.domain.statuses import Platform, CampaignType, AudienceSource
from typing import List, Tuple

def validate_url(url: str) -> Tuple[bool, str]:
    if not url:
        return True, ""
    try:
        parsed = urlparse(url.strip())
        if parsed.scheme not in ("http", "https"):
            return False, "Ссылка должна начинаться с https:// или http://"
        if not parsed.netloc:
            return False, "Некорректный URL: отсутствует домен"
        if "." not in parsed.netloc:
            return False, "Некорректный URL: некорректный домен"
        return True, ""
    except Exception:
        return False, "Некорректный URL"

def validate_campaign(c: Campaign) -> Tuple[bool, List[str]]:
    errors = []
    if c.platform not in Platform.all_values():
        errors.append(f"Неизвестная платформа: {c.platform}")
    if not c.message_text or len(c.message_text.strip()) < 5:
        errors.append("Текст сообщения слишком короткий (минимум 5 символов)")
    if len(c.message_text) > 4096:
        errors.append("Текст слишком длинный: максимум 4096 символов (ограничение Telegram)")
    if not c.country or len(c.country.strip()) < 2:
        errors.append("Укажите страну (минимум 2 символа)")
    if c.requested_limit < 0:
        errors.append("Лимит не может быть отрицательным")
    if c.requested_limit > 10000:
        errors.append("Лимит слишком большой: максимум 10000 за одну кампанию")
    ok, msg = validate_url(c.link)
    if not ok:
        errors.append(msg)
    if not c.audience_source:
        errors.append("Укажите источник аудитории")
    # campaign_type validation
    allowed_types = [e.value for e in CampaignType]
    if c.campaign_type not in allowed_types:
        errors.append(f"Неизвестный тип кампании: {c.campaign_type}")
    return (len(errors) == 0, errors)

def validate_country_city(country: str, city: str) -> Tuple[bool, str]:
    if not country or len(country.strip()) < 2:
        return False, "Укажите страну (минимум 2 символа), например: Украина"
    # Проверка через единый справочник — защита от неверной страны из-за некорректного поиска
    from app.data.countries import is_valid_country
    if country and not is_valid_country(country):
        return False, f"Страна «{country}» не найдена в справочнике. Выберите из списка с поиском."
    if city and len(city.strip()) < 2:
        return False, "Название города слишком короткое"
    return True, ""

def validate_country_search(query: str) -> Tuple[bool, List[dict]]:
    """Используется для проверки поиска: возвращает результаты."""
    from app.data.countries import search_countries
    results = search_countries(query)
    return len(results) > 0, results
