"""
i18n модуль:
- Приоритет: 1) явный выбор пользователя 2) сохранённое предпочтение 3) язык Telegram 4) fallback ru
- Поддержка ru/en/uk, единые ключи
- Не определяет язык по одному случайному слову — предлагает выбор кнопками.
"""
from typing import Optional

# импортируем локали
from .locales.ru import STRINGS as RU
from .locales.en import STRINGS as EN
from .locales.uk import STRINGS as UK

LOCALES = {"ru": RU, "en": EN, "uk": UK}
SUPPORTED = ["ru", "en", "uk"]
DEFAULT = "ru"

# кэш в памяти для скорости (дополняет БД)
_lang_cache: dict[int, str] = {}

def normalize_lang(code: str) -> str:
    if not code:
        return DEFAULT
    c = code.lower().strip()[:2]
    if c in SUPPORTED:
        return c
    # маппим распространённые коды Telegram
    mapping = {"ua": "uk", "us": "en", "gb": "en"}
    return mapping.get(c, DEFAULT)

def detect_language(telegram_lang_code: Optional[str], text: Optional[str] = None) -> str:
    """
    Определение языка: по Telegram lang_code если доступен, иначе fallback.
    Не гадает по одному слову — если текст короткий/неуверенный, возвращает DEFAULT.
    """
    if telegram_lang_code:
        return normalize_lang(telegram_lang_code)
    # простая эвристика по тексту — только если явно много кириллицы
    if text and len(text) > 10:
        # если есть украинские специфичные буквы
        if any(ch in text for ch in "їєґіІЇЄҐ"):
            return "uk"
        # если кириллица преобладает
        cyr = sum(1 for ch in text if "а" <= ch.lower() <= "я" or ch in "ёЁ")
        if cyr / len(text) > 0.3:
            return "ru"
    return DEFAULT

def get_user_lang(user_id: int, db_language: str = None, tg_code: str = None) -> str:
    # 1. явный выбор (БД)
    if db_language and db_language in SUPPORTED:
        return db_language
    # 2. кэш
    if user_id in _lang_cache:
        return _lang_cache[user_id]
    # 3. Telegram
    if tg_code:
        return normalize_lang(tg_code)
    return DEFAULT

def set_user_lang(user_id: int, lang: str):
    _lang_cache[user_id] = normalize_lang(lang)

def t(key: str, lang: str = "ru", **kwargs) -> str:
    """Перевод по ключу с подстановкой."""
    locale = LOCALES.get(normalize_lang(lang), RU)
    template = locale.get(key) or RU.get(key) or key
    if kwargs:
        try:
            return template.format(**kwargs)
        except:
            return template
    return template
