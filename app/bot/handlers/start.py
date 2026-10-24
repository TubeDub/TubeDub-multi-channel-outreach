from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from app.bot.keyboards import main_menu_keyboard
from app.services.consent_service import ConsentService
from app.services.subscription_service import SubscriptionService
from app.config import DATABASE_PATH
from app.i18n.translator import t, detect_language, get_user_lang, set_user_lang
from app.storage.repositories import SettingsRepo, UserRepo

WELCOME = (
    "✨ <b>MultiChannel Outreach</b> — профессиональный центр рассылок\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "Создавайте кампании для <b>Telegram, Messenger, Instagram, WhatsApp, TikTok, Email</b> в одном месте.\n\n"
    "🎁 <b>Старт:</b> 10 бесплатных рассылок для каждого нового пользователя\n"
    "💎 Подписка: <b>$1/мес</b> — после пробного периода\n\n"
    "Выберите действие в меню ниже:"
)

HELP_TEXT = (
    "❓ <b>Помощь — MultiChannel Outreach</b>\n\n"
    "🚀 <b>Создать кампанию</b> — 8 шагов: канал → аудитория → получатели → текст → ссылка → предпросмотр → подтверждение → запуск\n"
    "📋 <b>Мои кампании</b> — список, карточка с действиями, редактирование/дубль/удаление\n"
    "📊 <b>Статистика</b> — отправлено/ошибки/пропущено по каждой кампании\n"
    "🔌 <b>Подключения</b> — статус каналов (connected/not_connected/configuration_error/permission_error/service_error)\n"
    "🔍 <b>Диагностика</b> — /diagnostics проверяет каждый канал без массовой отправки\n"
    "👤 <b>Мой аккаунт</b> — лимит 10 бесплатных, остаток, подписка, expiry\n"
    "💎 <b>Подписка</b> — оформление $1/30 дней, ручное подтверждение админом\n"
    "⚙️ <b>Настройки</b> — страна (список с поиском), язык, часовой пояс, тест-режим\n\n"
    "Команды: /start, /menu, /help, /diagnostics, /language, /cancel, /stop, /account, /stats\n"
    "• /cancel — отменить шаг без потери кампаний\n"
    "• /stop — отписаться от рассылок\n\n"
    "⚠️ География — параметр таргетинга, не список людей. Отправка только с согласия.\n"
)

async def _ensure_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    tg_lang = getattr(user, 'language_code', None)
    # detect
    detected = detect_language(tg_lang, update.message.text if update.message else None)
    try:
        srepo = SettingsRepo(DATABASE_PATH)
        s = await srepo.get(user.id)
        # если язык ещё не выбран — сохраняем detected
        if not s.language or s.language == "ru":
            # но если уже есть — не перезаписываем, уважаем выбор пользователя (приоритет 1)
            # проверим users тоже
            urepo = UserRepo(DATABASE_PATH)
            u = await urepo.get(user.id)
            if not u or not getattr(u, 'language', None) or u.language == "ru":
                # первая регистрация — ставим detected если не ru
                if detected != "ru":
                    s.language = detected
                    await srepo.upsert(s)
                    if u:
                        u.language = detected
                        await urepo.upsert(u)
        # кэш
        lang = s.language or detected
        set_user_lang(user.id, lang)
        context.user_data["lang"] = lang
        return lang
    except:
        return detected

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = await _ensure_language(update, context)
    # grant consent
    try:
        cs = ConsentService(DATABASE_PATH)
        await cs.grant(user.id, "telegram", str(user.id), source="bot_start", display_name=user.full_name)
    except Exception:
        pass
    # ensure user exists for subscription + language
    try:
        sub = SubscriptionService(DATABASE_PATH)
        u = await sub.get_or_create_user(user.id, username=user.username or "", first_name=user.full_name or "")
        # сохранить язык если новый
        if getattr(u, 'language', 'ru') != lang:
            u.language = lang
            from app.storage.repositories import UserRepo
            await UserRepo(DATABASE_PATH).upsert(u)
    except Exception:
        pass
    # если язык не ru — предложить выбор
    if lang != "ru":
        await update.message.reply_text(t("welcome_title", lang), parse_mode="HTML")
        await update.message.reply_text(t("welcome_body", lang), reply_markup=main_menu_keyboard(lang), parse_mode="HTML")
    else:
        await update.message.reply_text(WELCOME, reply_markup=main_menu_keyboard(lang), parse_mode="HTML")
    # Если первый визит — показать приветствие 8 шагов регистрации
    if not context.user_data.get("welcomed"):
        context.user_data["welcomed"] = True

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang") or "ru"
    await update.message.reply_text(t("main_menu", lang), reply_markup=main_menu_keyboard(lang), parse_mode="HTML")

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang") or "ru"
    await update.message.reply_text(t("help_text", lang) if t("help_text", lang) != "help_text" else HELP_TEXT, parse_mode="HTML")

async def language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang") or "ru"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="set_lang:ru")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="set_lang:en")],
        [InlineKeyboardButton("🇺🇦 Українська", callback_data="set_lang:uk")],
        [InlineKeyboardButton(t("btn_cancel", lang), callback_data="go_menu")],
    ])
    await update.message.reply_text(t("language_pick", lang), reply_markup=kb)

async def handle_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    code = query.data.split(":")[1]
    user_id = update.effective_user.id
    set_user_lang(user_id, code)
    context.user_data["lang"] = code
    try:
        srepo = SettingsRepo(DATABASE_PATH)
        s = await srepo.get(user_id)
        s.language = code
        await srepo.upsert(s)
        urepo = UserRepo(DATABASE_PATH)
        u = await urepo.get(user_id)
        if u:
            u.language = code
            await urepo.upsert(u)
    except:
        pass
    await query.edit_message_text(f"✅ Язык изменён: {code}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Меню", callback_data="go_menu")]]))

async def stop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cs = ConsentService(DATABASE_PATH)
    await cs.revoke(user.id, "telegram", str(user.id))
    await update.message.reply_text("✅ Вы отписались. Бот больше не будет писать вам.\nЧтобы подписаться снова — /start")

async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("wizard", None)
    context.user_data.pop("country_picker", None)
    context.user_data.pop("language_picker", None)
    context.user_data.pop("edit_state", None)
    context.user_data.pop("awaiting_setting", None)
    context.user_data.pop("awaiting_channel", None)
    lang = context.user_data.get("lang") or "ru"
    await update.message.reply_text("↩️ Операция отменена. Данные сохранены.", reply_markup=main_menu_keyboard(lang))

async def unknown_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # приоритет: picker
    if context.user_data.get("country_picker"):
        from app.bot.handlers.pickers import build_country_picker
        q = update.message.text.strip()
        # обновляем список — поиск без Enter
        lang = context.user_data.get("lang") or "ru"
        picker = context.user_data["country_picker"]
        text, kb = build_country_picker(query=q, page=0, selected=picker.get("selected", []), lang=lang)
        picker["query"] = q
        picker["page"] = 0
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")
        return
    if "wizard" in context.user_data:
        from app.bot.handlers.wizard import handle_wizard_text
        await handle_wizard_text(update, context)
        return
    if "edit_state" in context.user_data:
        from app.bot.handlers.campaigns import handle_edit_text
        await handle_edit_text(update, context)
        return
    text = update.message.text.strip()
    mapping = {
        "🚀 Создать кампанию": "wizard",
        "➕ Создать кампанию": "wizard",
        "📋 Мои кампании": "campaigns",
        "📊 Статистика": "stats",
        "📊 Отчёты": "reports",
        "🕘 История": "history",
        "🔌 Подключения": "connections",
        "🔍 Диагностика": "diagnostics",
        "👥 Мои аккаунты": "accounts",
        "👥 Аудитории": "audiences",
        "👤 Мой аккаунт": "account",
        "💎 Подписка": "subscription",
        "⚙️ Настройки": "settings",
        "❓ Помощь": "help",
        "🌐 Язык": "language",
    }
    action = mapping.get(text)
    if action == "wizard":
        from app.bot.handlers.wizard import start_wizard
        await start_wizard(update, context)
    elif action == "campaigns":
        from app.bot.handlers.campaigns import list_campaigns
        await list_campaigns(update, context)
    elif action == "stats":
        from app.bot.handlers.stats import show_stats
        await show_stats(update, context)
    elif action == "reports":
        from app.bot.handlers.history import show_reports
        await show_reports(update, context)
    elif action == "history":
        from app.bot.handlers.history import show_history
        await show_history(update, context)
    elif action == "connections":
        from app.bot.handlers.integrations import show_connections
        await show_connections(update, context)
    elif action == "diagnostics":
        from app.bot.handlers.diagnostics import show_diagnostics
        await show_diagnostics(update, context)
    elif action == "accounts":
        from app.bot.handlers.accounts import show_accounts
        await show_accounts(update, context)
    elif action == "audiences":
        from app.bot.handlers.audiences import show_audiences
        await show_audiences(update, context)
    elif action == "account":
        from app.bot.handlers.account import show_account
        await show_account(update, context)
    elif action == "subscription":
        from app.bot.handlers.subscription import show_subscription
        await show_subscription(update, context)
    elif action == "settings":
        from app.bot.handlers.settings import show_settings
        await show_settings(update, context)
    elif action == "help":
        await help_handler(update, context)
    elif action == "language":
        await language_handler(update, context)
    else:
        lang = context.user_data.get("lang") or "ru"
        await update.message.reply_text("Не понял. Выберите действие в меню или нажмите /help", reply_markup=main_menu_keyboard(lang))
