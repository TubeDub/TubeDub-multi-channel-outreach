from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from app.config import DATABASE_PATH
from app.storage.repositories import SettingsRepo

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else 0
    lang = context.user_data.get("lang") or "ru"
    repo = SettingsRepo(DATABASE_PATH)
    s = await repo.get(user_id)
    from app.i18n.translator import t
    text = (
        f"⚙️ <b>{t('btn_settings', lang)}</b>\n\n"
        f"🌍 Страна по умолчанию: {s.default_country or 'не задана'}\n"
        f"🌐 Язык: {s.language}\n"
        f"🕐 Часовой пояс: {s.timezone}\n"
        f"🧪 Режим тестирования: {'Вкл' if s.test_mode else 'Выкл'}\n"
        f"🔔 Уведомления: {'Вкл' if s.notifications else 'Выкл'}\n"
        f"📦 Лимит очереди: {s.queue_limit}\n\n"
        f"Страна выбирается из списка с поиском (нажми 🌍), язык — 🌐.\n"
        f"Секреты не хранятся в чате и не показываются."
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 Изменить страну", callback_data="settings_country_picker")],
        [InlineKeyboardButton("🌐 Изменить язык", callback_data="set_lang_picker")],
        [InlineKeyboardButton("🕐 Изменить часовой пояс", callback_data="settings_edit:tz")],
        [InlineKeyboardButton(f"🧪 Тест-режим: {'Выкл' if s.test_mode else 'Вкл'}", callback_data="settings_edit:testmode")],
        [InlineKeyboardButton(f"🔔 Уведомления: {'Выкл' if s.notifications else 'Вкл'}", callback_data="settings_edit:notif")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="go_menu")],
    ])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

async def handle_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "settings_country_picker":
        from app.bot.handlers.pickers import build_country_picker
        lang = context.user_data.get("lang") or "ru"
        context.user_data["country_picker"] = {"query":"", "page":0, "selected":[], "mode":"settings", "lang":lang}
        text, kb = build_country_picker(query="", page=0, selected=[], lang=lang)
        await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
        return
    elif data == "set_lang_picker":
        from app.bot.handlers.pickers import build_language_picker
        lang = context.user_data.get("lang") or "ru"
        text, kb = build_language_picker(query="", page=0, lang=lang)
        context.user_data["language_picker"] = {"query":"", "page":0, "lang":lang}
        await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
        return
    elif data.startswith("pick_country:"):
        code = data.split(":")[1]
        picker = context.user_data.get("country_picker", {})
        selected = picker.get("selected", [])
        # single-select для настроек
        if code in selected:
            selected.remove(code)
        else:
            selected = [code]
        picker["selected"] = selected
        from app.bot.handlers.pickers import build_country_picker
        lang = context.user_data.get("lang") or "ru"
        text, kb = build_country_picker(query=picker.get("query",""), page=picker.get("page",0), selected=selected, lang=lang)
        await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
        return
    elif data.startswith("pick_country_page:"):
        parts = data.split(":")
        page = int(parts[1])
        q = parts[2] if len(parts)>2 else ""
        picker = context.user_data.get("country_picker", {})
        picker["page"] = page
        picker["query"] = q
        from app.bot.handlers.pickers import build_country_picker
        lang = context.user_data.get("lang") or "ru"
        text, kb = build_country_picker(query=q, page=page, selected=picker.get("selected", []), lang=lang)
        await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
        return
    elif data == "pick_country_confirm":
        picker = context.user_data.pop("country_picker", None)
        selected = picker.get("selected", []) if picker else []
        if selected:
            from app.data.countries import get_country
            c = get_country(selected[0])
            name = c["name_ru"] if c else selected[0]
            user_id = update.effective_user.id
            repo = SettingsRepo(DATABASE_PATH)
            s = await repo.get(user_id)
            s.default_country = name
            await repo.upsert(s)
            await query.edit_message_text(f"✅ Страна изменена: {name}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Меню", callback_data="go_menu")]]))
        else:
            await query.edit_message_text("⚠️ Страна не выбрана", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Меню", callback_data="go_menu")]]))
        return
    elif data == "pick_country_cancel":
        context.user_data.pop("country_picker", None)
        await show_settings(update, context)
        return
    elif data.startswith("pick_lang:"):
        code = data.split(":")[1]
        user_id = update.effective_user.id
        from app.i18n.translator import set_user_lang
        set_user_lang(user_id, code)
        context.user_data["lang"] = code
        context.user_data.pop("language_picker", None)
        # сохранить в БД
        repo = SettingsRepo(DATABASE_PATH)
        s = await repo.get(user_id)
        s.language = code
        await repo.upsert(s)
        from app.storage.repositories import UserRepo
        ur = UserRepo(DATABASE_PATH)
        u = await ur.get(user_id)
        if u:
            u.language = code
            await ur.upsert(u)
        await query.edit_message_text(f"✅ Язык изменён: {code}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Меню", callback_data="go_menu")]]))
        return
    elif data.startswith("pick_lang_page:"):
        parts = data.split(":")
        page = int(parts[1])
        q = parts[2] if len(parts)>2 else ""
        from app.bot.handlers.pickers import build_language_picker
        lang = context.user_data.get("lang") or "ru"
        text, kb = build_language_picker(query=q, page=page, lang=lang)
        picker = context.user_data.get("language_picker", {})
        picker["page"] = page
        picker["query"] = q
        await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
        return
    elif data == "pick_lang_cancel":
        context.user_data.pop("language_picker", None)
        await show_settings(update, context)
        return
    elif data == "settings_edit:country":
        context.user_data["awaiting_setting"] = "country"
        await query.edit_message_text("Введите страну по умолчанию, например: Украина", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="go_settings")]]))
    elif data == "settings_edit:tz":
        context.user_data["awaiting_setting"] = "tz"
        await query.edit_message_text("Введите часовой пояс, например: Europe/Kiev", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="go_settings")]]))
    elif data == "settings_edit:testmode":
        user_id = update.effective_user.id
        repo = SettingsRepo(DATABASE_PATH)
        s = await repo.get(user_id)
        s.test_mode = 0 if s.test_mode else 1
        await repo.upsert(s)
        await show_settings(update, context)
    elif data == "settings_edit:notif":
        user_id = update.effective_user.id
        repo = SettingsRepo(DATABASE_PATH)
        s = await repo.get(user_id)
        s.notifications = 0 if s.notifications else 1
        await repo.upsert(s)
        await show_settings(update, context)
    elif data == "go_settings":
        await show_settings(update, context)

async def handle_settings_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # приоритет: country picker поиск
    if context.user_data.get("country_picker"):
        from app.bot.handlers.pickers import build_country_picker
        q = update.message.text.strip()
        lang = context.user_data.get("lang") or "ru"
        picker = context.user_data["country_picker"]
        text, kb = build_country_picker(query=q, page=0, selected=picker.get("selected", []), lang=lang)
        picker["query"] = q
        picker["page"] = 0
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")
        return True
    if context.user_data.get("language_picker"):
        from app.bot.handlers.pickers import build_language_picker
        q = update.message.text.strip()
        lang = context.user_data.get("lang") or "ru"
        text, kb = build_language_picker(query=q, page=0, lang=lang)
        context.user_data["language_picker"]["query"] = q
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")
        return True
    awaiting = context.user_data.get("awaiting_setting")
    if not awaiting:
        return False
    user_id = update.effective_user.id
    repo = SettingsRepo(DATABASE_PATH)
    s = await repo.get(user_id)
    val = update.message.text.strip()
    if awaiting == "country":
        from app.data.countries import is_valid_country
        if not is_valid_country(val):
            await update.message.reply_text(f"⚠️ Страна «{val}» не найдена. Выберите из списка 🌍.")
            return True
        s.default_country = val
    elif awaiting == "tz":
        s.timezone = val
    await repo.upsert(s)
    context.user_data.pop("awaiting_setting", None)
    await update.message.reply_text(f"✅ Настройка сохранена: {awaiting} = {val}")
    await show_settings(update, context)
    return True
