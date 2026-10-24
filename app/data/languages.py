"""
Единый справочник языков — аналогично странам.
Используется для выбора языка интерфейса и сегментации.
"""
from typing import List, Dict

LANGUAGES: List[Dict] = [
    {"code": "ru", "name_ru": "Русский", "name_en": "Russian", "name_uk": "Російська", "flag": "🇷🇺", "aliases": ["русский", "russian", "ru", "rus"]},
    {"code": "uk", "name_ru": "Украинский", "name_en": "Ukrainian", "name_uk": "Українська", "flag": "🇺🇦", "aliases": ["украинский", "ukrainian", "українська", "uk", "ukr"]},
    {"code": "en", "name_ru": "Английский", "name_en": "English", "name_uk": "Англійська", "flag": "🇬🇧", "aliases": ["английский", "english", "англійська", "en"]},
    {"code": "de", "name_ru": "Немецкий", "name_en": "German", "name_uk": "Німецька", "flag": "🇩🇪", "aliases": ["немецкий", "german", "німецька", "de", "deutsch"]},
    {"code": "fr", "name_ru": "Французский", "name_en": "French", "name_uk": "Французька", "flag": "🇫🇷", "aliases": ["французский", "french", "французька", "fr"]},
    {"code": "es", "name_ru": "Испанский", "name_en": "Spanish", "name_uk": "Іспанська", "flag": "🇪🇸", "aliases": ["испанский", "spanish", "іспанська", "es"]},
    {"code": "pl", "name_ru": "Польский", "name_en": "Polish", "name_uk": "Польська", "flag": "🇵🇱", "aliases": ["польский", "polish", "польська", "pl"]},
    {"code": "tr", "name_ru": "Турецкий", "name_en": "Turkish", "name_uk": "Турецька", "flag": "🇹🇷", "aliases": ["турецкий", "turkish", "турецька", "tr"]},
    {"code": "it", "name_ru": "Итальянский", "name_en": "Italian", "name_uk": "Італійська", "flag": "🇮🇹", "aliases": ["итальянский", "italian", "італійська", "it"]},
    {"code": "pt", "name_ru": "Португальский", "name_en": "Portuguese", "name_uk": "Португальська", "flag": "🇵🇹", "aliases": ["португальский", "portuguese", "португальська", "pt"]},
    {"code": "ar", "name_ru": "Арабский", "name_en": "Arabic", "name_uk": "Арабська", "flag": "🇸🇦", "aliases": ["арабский", "arabic", "ar"]},
    {"code": "zh", "name_ru": "Китайский", "name_en": "Chinese", "name_uk": "Китайська", "flag": "🇨🇳", "aliases": ["китайский", "chinese", "zh"]},
    {"code": "ja", "name_ru": "Японский", "name_en": "Japanese", "name_uk": "Японська", "flag": "🇯🇵", "aliases": ["японский", "japanese", "ja"]},
    {"code": "ko", "name_ru": "Корейский", "name_en": "Korean", "name_uk": "Корейська", "flag": "🇰🇷", "aliases": ["корейский", "korean", "ko"]},
    {"code": "hi", "name_ru": "Хинди", "name_en": "Hindi", "name_uk": "Хінді", "flag": "🇮🇳", "aliases": ["хинди", "hindi", "hi"]},
    {"code": "kk", "name_ru": "Казахский", "name_en": "Kazakh", "name_uk": "Казахська", "flag": "🇰🇿", "aliases": ["казахский", "kazakh", "kk"]},
    {"code": "ro", "name_ru": "Румынский", "name_en": "Romanian", "name_uk": "Румунська", "flag": "🇷🇴", "aliases": ["румынский", "romanian", "ro"]},
    {"code": "hu", "name_ru": "Венгерский", "name_en": "Hungarian", "name_uk": "Угорська", "flag": "🇭🇺", "aliases": ["венгерский", "hungarian", "hu"]},
    {"code": "cs", "name_ru": "Чешский", "name_en": "Czech", "name_uk": "Чеська", "flag": "🇨🇿", "aliases": ["чешский", "czech", "cs"]},
    {"code": "nl", "name_ru": "Нидерландский", "name_en": "Dutch", "name_uk": "Нідерландська", "flag": "🇳🇱", "aliases": ["нидерландский", "dutch", "nl"]},
]

_BY_CODE = {l["code"]: l for l in LANGUAGES}

def get_language(code: str):
    return _BY_CODE.get((code or "").lower())

def search_languages(query: str, limit: int = 10):
    q = (query or "").strip().lower()
    if not q:
        return LANGUAGES[:10]
    scored = []
    for l in LANGUAGES:
        names = [l["name_ru"].lower(), l["name_en"].lower(), l["name_uk"].lower(), l["code"].lower()]
        aliases = [a.lower() for a in l.get("aliases", [])]
        score = 0
        if q in names:
            score = 100
        elif any(a == q for a in aliases):
            score = 95
        elif any(n.startswith(q) for n in names):
            score = 80
        elif any(a.startswith(q) for a in aliases):
            score = 75
        elif any(q in n for n in names):
            score = 50
        elif any(q in a for a in aliases):
            score = 45
        else:
            continue
        if score:
            scored.append((score, l))
    scored.sort(key=lambda x: (-x[0], x[1]["name_ru"]))
    return [l for _, l in scored[:limit]]

def format_language(l: Dict, lang: str = "ru") -> str:
    name = l.get(f"name_{lang}", l["name_ru"])
    return f"{l['flag']} {name} ({l['code']})"
