"""
Универсальные питкеры: страна/язык/канал с поиском без Enter.
Реализует ТЗ §5: нажатие открывает список с флагами, прокрутка, поиск по мере ввода,
учёт вариантов написания/регистра, выбор 1/нескольких, отображение в поле, удаление, Все страны/Не указана,
единый справочник.
"""
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from app.data.countries import search_countries, format_country, SPECIAL_OPTIONS, COUNTRIES
from app.data.languages import search_languages, format_language
from app.i18n.translator import t

PAGE_SIZE = 8

def build_country_picker(query: str = "", page: int = 0, selected: list = None, lang: str = "ru", multi: bool = False):
    selected = selected or []
    results = search_countries(query, lang=lang, limit=50)
    total = len(results)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    page_items = results[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]

    rows = []
    for c in page_items:
        code = c["code"]
        is_sel = code in selected
        check = "✅ " if is_sel else ""
        label = f"{check}{format_country(c, lang)}"
        cb = f"pick_country:{code}"
        rows.append([InlineKeyboardButton(label, callback_data=cb)])
    # пагинация
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"pick_country_page:{page-1}:{query}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"pick_country_page:{page+1}:{query}"))
    if nav:
        rows.append(nav)
    # выбранные chips + очистка
    if selected:
        chips = ", ".join(selected)
        rows.append([InlineKeyboardButton(f"🧹 Очистить ({chips})", callback_data="pick_country_clear")])
    # подтвердить/отмена
    rows.append([
        InlineKeyboardButton(t("btn_confirm", lang), callback_data="pick_country_confirm"),
        InlineKeyboardButton(t("btn_cancel", lang), callback_data="pick_country_cancel"),
    ])
    # подсказка
    text = (
        f"{t('country_pick', lang)}\n"
        f"{t('country_search_hint', lang)}\n\n"
        f"Запрос: <b>{query or '—'}</b> · стр {page+1}/{total_pages} · найдено {total}\n"
        f"Нажмите на страну для выбора. {'Можно несколько.' if multi else 'Одна страна.'}\n"
        f"Отправьте текст для поиска — обновится список.\n"
    )
    if selected:
        text += f"\n{t('country_selected', lang, country=', '.join(selected))}\n"
    return text, InlineKeyboardMarkup(rows)

def build_language_picker(query: str = "", page: int = 0, lang: str = "ru"):
    results = search_languages(query, limit=50)
    total = len(results)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    page_items = results[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]
    rows = []
    for l in page_items:
        label = format_language(l, lang)
        rows.append([InlineKeyboardButton(label, callback_data=f"pick_lang:{l['code']}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"pick_lang_page:{page-1}:{query}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"pick_lang_page:{page+1}:{query}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(t("btn_cancel", lang), callback_data="pick_lang_cancel")])
    text = f"{t('language_pick', lang)}\n{t('country_search_hint', lang)}\n\nЗапрос: <b>{query or '—'}</b> · стр {page+1}/{total_pages}\n"
    return text, InlineKeyboardMarkup(rows)

def is_country_picker_active(context) -> bool:
    return bool(context.user_data.get("country_picker"))

def is_language_picker_active(context) -> bool:
    return bool(context.user_data.get("language_picker"))
