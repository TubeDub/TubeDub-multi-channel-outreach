from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from app.config import DATABASE_PATH
from app.bot.keyboards import connections_keyboard, connection_detail_keyboard
from app.providers.telegram_provider import TelegramProvider
from app.providers.telegram_user_provider import TelegramUserProvider
from app.providers.meta_messenger_provider import MetaMessengerProvider
from app.providers.instagram_provider import InstagramProvider
from app.providers.whatsapp_provider import WhatsAppProvider
from app.providers.tiktok_provider import TikTokProvider
from app.providers.email_provider import EmailProvider

PROVIDERS = {
    "telegram_user": TelegramUserProvider,
    "telegram": TelegramProvider,
    "facebook_messenger": MetaMessengerProvider,
    "instagram": InstagramProvider,
    "whatsapp": WhatsAppProvider,
    "tiktok": TikTokProvider,
    "email": EmailProvider,
}

STATUS_EMOJI = {
    "connected": "✅",
    "not_connected": "⚪",
    "configuration_error": "🟡",
    "permission_error": "🟠",
    "service_error": "🔴",
    "needs_permissions": "🟠",
    "unavailable": "🔴",
}

def _human_status(platform, status, hint, next_step=""):
    return f"<b>{platform}</b>: {STATUS_EMOJI.get(status,'•')} <b>{status}</b>\n   {hint}\n" + (f"   → {next_step}\n" if next_step else "")

async def show_connections(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else 0
    statuses = {}
    lines = "🔌 <b>Подключения — статус провайдеров</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for plat, ProvCls in PROVIDERS.items():
        prov = ProvCls(db_path=DATABASE_PATH)
        try:
            res = await prov.check_connection(owner_id=user_id)
        except Exception as e:
            res = {"status": "service_error", "hint": str(e), "next_step": "Попробуйте позже"}
        statuses[plat] = res
        lines += _human_status(plat, res.get("status","unknown"), res.get("hint",""), res.get("next_step",""))
        caps = res.get("capabilities") or await prov.get_capabilities()
        lines += f"   возможности: {', '.join([k for k,v in caps.items() if v]) or 'нет'}\n\n"
    lines += (
        "\n<b>Как подключить:</b>\n"
        "• <b>Telegram</b> — укажите TELEGRAM_BOT_TOKEN в .env (проверка через getMe, без вывода токена)\n"
        "• <b>Messenger</b> — META_ACCESS_TOKEN + Facebook Page + pages_messaging (Meta Graph API)\n"
        "• <b>Instagram</b> — Professional/Business + instagram_manage_messages\n"
        "• <b>WhatsApp</b> — WHATSAPP_TOKEN + Phone ID + Business verification + шаблоны\n"
        "• <b>TikTok</b> — TIKTOK_ACCESS_TOKEN + Business approval (массовая отправка недоступна)\n"
        "• <b>Email</b> — SMTP_HOST/USER/PASSWORD + подтверждённый отправитель\n"
        "Отсутствие одного канала <b>не ломает</b> остальные. Черновики всегда доступны.\n"
    )
    kb = connections_keyboard(statuses)
    if update.callback_query:
        await update.callback_query.edit_message_text(lines, reply_markup=kb, parse_mode="HTML")
    else:
        await update.message.reply_text(lines, reply_markup=kb, parse_mode="HTML")

async def check_single_provider(update: Update, context: ContextTypes.DEFAULT_TYPE, platform: str):
    user_id = update.effective_user.id
    ProvCls = PROVIDERS.get(platform)
    if not ProvCls:
        await update.callback_query.edit_message_text(f"Неизвестный провайдер: {platform}")
        return
    prov = ProvCls(db_path=DATABASE_PATH)
    res = await prov.check_connection(owner_id=user_id)
    status = res.get("status","unknown")
    hint = res.get("hint","")
    next_step = res.get("next_step","")
    caps = res.get("capabilities", {})
    required = res.get("required", [])
    text = (
        f"🔌 <b>Проверка — {platform}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Статус: {STATUS_EMOJI.get(status,'')} <b>{status}</b>\n"
        f"{hint}\n"
    )
    if next_step:
        text += f"След. шаг: {next_step}\n"
    if required:
        text += f"Требуется: {', '.join(required)}\n"
    text += f"\nВозможности: {', '.join([k for k,v in caps.items() if v]) or 'нет'}\n"

    if platform == "telegram_user":
        user = res.get("user",{})
        if status == "connected":
            text += f"\nЛичный: @{user.get('username','')} — {user.get('first_name','')}\nСессия: {res.get('account',{}).get('id','')} ✓\n"
            text += "\nОтправка от вашего имени через Telethon. Не путайте с ботом." 
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("📜 Мои диалоги", callback_data="conn_dialogs:telegram_user"), InlineKeyboardButton("❌ Отключить", callback_data="conn_disconnect:telegram_user")], [InlineKeyboardButton("⬅️ Назад", callback_data="go_connections")]])
        else:
            text += "\nПодключите: Мои аккаунты → Подключить личный Telegram (телефон+код+2FA)"
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Подключить личный", callback_data="conn_connect:telegram_user")], [InlineKeyboardButton("⬅️ Назад", callback_data="go_connections")]])
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
        return
    if platform == "telegram" and status == "connected":
        bot_info = res.get("bot", {})
        text += f"\nБот: @{bot_info.get('username','')} — {bot_info.get('first_name','')}\nТокен: скрыт ✓\n"
        text += "\nХотите отправить тестовое сообщение?"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✉️ Тест себе", callback_data=f"conn_sendtest:{platform}")],
            [InlineKeyboardButton("⚙️ Настроить канал", callback_data="conn_set_channel")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="go_connections")],
        ])
    elif platform == "telegram" and status != "connected":
        text += "\nПроверьте .env → TELEGRAM_BOT_TOKEN и перезапустите."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="go_connections")]])
    else:
        if status == "connected":
            text += "\n✅ Готов к отправке. Можно запускать кампании."
        else:
            text += "\nЧерновики доступны, отправка — после настройки. См. .env.example"
        kb = connection_detail_keyboard(platform, status)
    await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")

async def send_test_to_self(update: Update, context: ContextTypes.DEFAULT_TYPE, platform: str):
    user_id = update.effective_user.id
    if platform != "telegram":
        await update.callback_query.edit_message_text("Тест доступен только для Telegram.")
        return
    prov = TelegramProvider(db_path=DATABASE_PATH)
    res = await prov.check_connection(owner_id=user_id)
    if res.get("status") != "connected":
        await update.callback_query.edit_message_text(f"Нельзя отправить тест: {res.get('hint')}")
        return
    text = (
        f"✉️ <b>Подтвердите тестовую отправку</b>\n\n"
        f"Получатель: ваш чат ({user_id})\n"
        f"Текст: <i>«Тест MultiChannel — проверка подключения успешна!»</i>\n\n"
        f"Требуется явное подтверждение."
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Да, отправить", callback_data=f"conn_sendtest_confirm:{user_id}")],
        [InlineKeyboardButton("❌ Отмена", callback_data="go_connections")],
    ])
    await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")

async def send_test_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, target_id: str):
    user_id = update.effective_user.id
    prov = TelegramProvider(db_path=DATABASE_PATH)
    try:
        result = await prov.send_message(recipient=str(user_id), text="✅ Тест MultiChannel Outreach: проверка подключения успешна!", owner_id=user_id)
        await update.callback_query.edit_message_text(f"✅ Отправлено! message_id={result.get('message_id')}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="go_connections")]]))
        from app.storage.repositories import ActivityRepo
        repo = ActivityRepo(DATABASE_PATH)
        await repo.log(user_id, None, "test_sent", f"Тест себе: {result.get('message_id')}")
    except Exception as e:
        await update.callback_query.edit_message_text(f"❌ Ошибка: {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="go_connections")]]))

async def prompt_set_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting_channel"] = True
    await update.callback_query.edit_message_text(
        "⚙️ <b>Настройка канала</b>\n\n"
        "Отправьте @username или chat_id, где бот — администратор.\n"
        "Пример: @mychannel или -1001234567890",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="go_connections")]]), parse_mode="HTML"
    )

async def handle_channel_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_channel"):
        return False
    channel = update.message.text.strip()
    user_id = update.effective_user.id
    if not channel.startswith("@") and not channel.startswith("-"):
        await update.message.reply_text("Укажите @username или chat_id, например @mychannel")
        return True
    prov = TelegramProvider(db_path=DATABASE_PATH)
    await prov.set_default_channel(user_id, channel)
    context.user_data.pop("awaiting_channel", None)
    await update.message.reply_text(f"✅ Канал сохранён: {channel}\nТеперь публикации пойдут туда.")
    return True

async def handle_integrations_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "go_connections":
        await show_connections(update, context)
    elif data.startswith("conn_check:"):
        plat = data.split(":",1)[1]
        await check_single_provider(update, context, plat)
    elif data.startswith("conn_sendtest:"):
        plat = data.split(":",1)[1]
        await send_test_to_self(update, context, plat)
    elif data.startswith("conn_sendtest_confirm:"):
        target = data.split(":",1)[1]
        await send_test_confirm(update, context, target)
    elif data == "conn_set_channel":
        await prompt_set_channel(update, context)
    elif data.startswith("conn_connect:"):
        plat = data.split(":",1)[1]
        if plat == "telegram_user":
            from app.bot.handlers.accounts import handle_accounts_callback
            # delegate to accounts flow
            context.user_data["awaiting_phone"] = True
            await query.edit_message_text("📱 Подключение личного Telegram\nВведите номер в формате +380... (API_ID/HASH в .env уже заданы)", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="go_connections")]]))
        else:
            await query.edit_message_text(f"Для {plat} добавьте токены в .env → Проверить", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="go_connections")]]))
    elif data.startswith("conn_disconnect:"):
        plat = data.split(":",1)[1]
        if plat == "telegram_user":
            from pathlib import Path
            sess = Path(f"./data/sessions/user_{update.effective_user.id}.session")
            sess2 = Path(f"./data/sessions/{update.effective_user.id}.session")
            for s in [sess, sess2]:
                if s.exists():
                    s.unlink()
            await query.edit_message_text("✅ Личный аккаунт отключён", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="go_connections")]]))
        else:
            await query.edit_message_text("Отключите удалив токен из .env", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="go_connections")]]))
    elif data.startswith("conn_dialogs:"):
        plat = data.split(":",1)[1]
        from app.providers.telegram_user_provider import TelegramUserProvider
        prov = TelegramUserProvider(db_path=DATABASE_PATH)
        dialogs = await prov.get_available_dialogs(update.effective_user.id, limit=10)
        if not dialogs:
            await query.edit_message_text("Нет диалогов или не подключен", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="go_connections")]]))
        else:
            txt = "📜 Ваши доступные диалоги (только ваши, не спам):\n" + "\n".join([f"• {d.get('name')} ({d.get('id')})" for d in dialogs])
            await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="go_connections")]]))
