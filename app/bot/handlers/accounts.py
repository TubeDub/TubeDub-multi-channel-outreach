"""
Центр подключённых аккаунтов — карточки по каждому каналу
Показывает отправителя, статус, доступные функции, последнюю проверку, ошибки
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from app.config import DATABASE_PATH
from datetime import datetime
import os

PROVIDER_INFO = {
    "telegram_bot": {"name": "Telegram Бот", "icon": "🤖", "desc": "Управление, регистрация, уведомления. Отправитель — бот"},
    "telegram_user": {"name": "Telegram Личный", "icon": "👤", "desc": "Отправка от вашего имени через Telethon"},
    "facebook_messenger": {"name": "Facebook Messenger", "icon": "💬", "desc": "Сообщения от имени Page"},
    "instagram": {"name": "Instagram", "icon": "📸", "desc": "Direct через официальный API"},
    "whatsapp": {"name": "WhatsApp", "icon": "📞", "desc": "Cloud API + шаблоны"},
    "tiktok": {"name": "TikTok", "icon": "🎵", "desc": "Публикация/DM если доступно"},
    "email": {"name": "Email", "icon": "✉️", "desc": "SMTP / API"},
}

async def show_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else 0
    text = "👥 <b>Мои аккаунты — центр подключений</b>\n━━━━━━━━━━━━━━━\nВыберите отправителя. Каждый канал независим.\n\n"
    rows = []
    # Проверяем каждый
    for pid, info in PROVIDER_INFO.items():
        # Map to actual provider class
        status, hint, account = await _check_account(pid, user_id)
        emoji = {"connected":"✅","not_connected":"⚪","configuration_error":"🟡","permission_error":"🟠","service_error":"🔴"}.get(status,"•")
        # лимитер статус краткий
        try:
            from app.services.account_rate_limiter import AccountRateLimiter
            lim = AccountRateLimiter(DATABASE_PATH)
            await lim.init()
            plat_map2={"telegram_user":"telegram","facebook_messenger":"facebook_messenger","instagram":"instagram","whatsapp":"whatsapp","tikTok":"tiktok","email":"email"}
            plat2 = plat_map2.get(pid, pid.split("_")[0] if "_" in pid else pid)
            if pid in ("telegram_user","telegram_bot"):
                plat2="telegram"
            smsg = await lim.get_status_message(user_id, plat2)
            # сокращаем
            hint_short = hint + f"\n   {smsg[:120]}"
        except:
            hint_short = hint
        line = f"{emoji} <b>{info['icon']} {info['name']}</b> — <b>{status}</b>\n   {hint_short}\n"
        if account:
            line += f"   Аккаунт: {account}\n"
        line += f"   {info['desc']}\n\n"
        text += line
        rows.append([InlineKeyboardButton(f"{emoji} {info['name']} — {status}", callback_data=f"acc_detail:{pid}")])

    text += (
        "\n<b>Действия:</b>\n"
        "• <b>Telegram личный</b>: API ID/HASH с my.telegram.org → Подключить → номер → код → 2FA\n"
        "• <b>Messenger</b>: META_ACCESS_TOKEN + Page в .env → Проверить\n"
        "• <b>Instagram</b>: Professional аккаунт + права instagram_manage_messages\n"
        "• Все аккаунты изолированы — ошибка одного не блокирует остальные\n"
    )
    rows.append([InlineKeyboardButton("🔍 Диагностика", callback_data="go_diagnostics")])
    rows.append([InlineKeyboardButton("🏠 Главное меню", callback_data="go_menu")])
    kb = InlineKeyboardMarkup(rows)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

async def _check_account(pid: str, owner_id: int):
    try:
        if pid == "telegram_bot":
            from app.providers.telegram_provider import TelegramProvider
            p = TelegramProvider(db_path=DATABASE_PATH)
            r = await p.check_connection(owner_id=owner_id)
            acc = r.get("bot",{}).get("username") if r.get("bot") else None
            return r.get("status"), r.get("hint"), f"@{acc}" if acc else None
        elif pid == "telegram_user":
            from app.providers.telegram_user_provider import TelegramUserProvider
            p = TelegramUserProvider(db_path=DATABASE_PATH)
            r = await p.check_connection(owner_id=owner_id)
            acc = r.get("account",{}).get("session") if r.get("account") else None
            # Показываем phone если есть
            if acc:
                acc = f"Сессия {owner_id}"
            else:
                acc = None
            return r.get("status"), r.get("hint"), acc
        elif pid == "facebook_messenger":
            from app.providers.meta_messenger_provider import MetaMessengerProvider
            p=MetaMessengerProvider(db_path=DATABASE_PATH)
            r=await p.check_connection(owner_id)
            return r.get("status"), r.get("hint"), None
        elif pid == "instagram":
            from app.providers.instagram_provider import InstagramProvider
            p=InstagramProvider(db_path=DATABASE_PATH)
            r=await p.check_connection(owner_id)
            return r.get("status"), r.get("hint"), None
        elif pid == "whatsapp":
            from app.providers.whatsapp_provider import WhatsAppProvider
            p=WhatsAppProvider(db_path=DATABASE_PATH)
            r=await p.check_connection(owner_id)
            return r.get("status"), r.get("hint"), None
        elif pid == "tiktok":
            from app.providers.tiktok_provider import TikTokProvider
            p=TikTokProvider(db_path=DATABASE_PATH)
            r=await p.check_connection(owner_id)
            return r.get("status"), r.get("hint"), None
        elif pid == "email":
            from app.providers.email_provider import EmailProvider
            p=EmailProvider(db_path=DATABASE_PATH)
            r=await p.check_connection(owner_id)
            return r.get("status"), r.get("hint"), None
    except Exception as e:
        return "service_error", str(e), None
    return "not_connected", "Не подключён", None

async def show_account_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, pid: str):
    user_id = update.effective_user.id
    info = PROVIDER_INFO.get(pid, {"name": pid, "icon": "•", "desc": ""})
    status, hint, account = await _check_account(pid, user_id)
    # Добавляем статус лимитера для пользователя
    try:
        from app.services.account_rate_limiter import AccountRateLimiter
        limiter = AccountRateLimiter(DATABASE_PATH)
        await limiter.init()
        # маппим pid к platform
        plat_map={"telegram_user":"telegram","telegram_bot":"telegram","facebook_messenger":"facebook_messenger","instagram":"instagram","whatsapp":"whatsapp","email":"email","tiktok":"tiktok"}
        plat = plat_map.get(pid, pid)
        limiter_msg = await limiter.get_status_message(user_id, plat)
        # показываем только для основного telegram
        if pid in ("telegram_user","telegram"):
            hint = hint + f"\n📊 Лимитер: {limiter_msg}"
    except:
        pass
    emoji = {"connected":"✅","not_connected":"⚪","configuration_error":"🟡","permission_error":"🟠","service_error":"🔴"}.get(status,"•")
    text = (
        f"{emoji} <b>{info['icon']} {info['name']} — {status}</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{hint}\n"
    )
    if account:
        text += f"Аккаунт: {account}\n"
    text += f"{info['desc']}\n"

    # Добавляем специфичные инструкции
    if pid == "telegram_user":
        text += (
            "\n<b>Подключение личного аккаунта:</b>\n"
            "1. Получите API_ID и API_HASH на https://my.telegram.org → API development tools\n"
            "2. Добавьте в .env: TELEGRAM_API_ID, TELEGRAM_API_HASH\n"
            "3. Нажмите Подключить → введите номер в формате +380...\n"
            "4. Введите код из Telegram → 2FA пароль если включена\n"
            "5. Сессия сохранится в data/sessions/{user_id}.session (не в репозиторий!)\n"
            "\n⚠️ Не сохраняйте пароли/коды в репозитории, не выводите в логах. Сессии изолированы по пользователям.\n"
            "Доступные источники после подключения: ваши диалоги, контакты, каналы где вы админ. Писать можно только тем, кому разрешено по правилам платформы.\n"
        )
    elif pid == "telegram_bot":
        text += "\nБот используется как интерфейс управления, но не подменяет личный аккаунт как отправителя. Выберите отправителя в мастере кампании.\n"
        if status=="connected":
            text += "✅ Бот проверен через getMe, токен скрыт\n"
    elif pid in ("facebook_messenger","instagram"):
        text += "\nТребует Meta App, токен Page, разрешения pages_messaging / instagram_manage_messages. Подробно: developers.facebook.com\n"

    # Кнопки
    rows = []
    if pid=="telegram_user" and status!="connected":
        rows.append([InlineKeyboardButton("🔗 Подключить личный", callback_data=f"acc_connect:{pid}")])
    elif status=="connected":
        rows.append([InlineKeyboardButton("🔄 Проверить", callback_data=f"acc_detail:{pid}"), InlineKeyboardButton("❌ Отключить", callback_data=f"acc_disconnect:{pid}")])
    else:
        rows.append([InlineKeyboardButton("🔗 Подключить", callback_data=f"acc_connect:{pid}")])
        rows.append([InlineKeyboardButton("🔄 Проверить", callback_data=f"acc_detail:{pid}")])
    rows.append([InlineKeyboardButton("⬅️ Назад к аккаунтам", callback_data="go_accounts")])
    rows.append([InlineKeyboardButton("🏠 Главное меню", callback_data="go_menu")])
    kb=InlineKeyboardMarkup(rows)
    await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")

async def handle_accounts_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query
    await query.answer()
    data=query.data
    if data=="go_accounts":
        await show_accounts(update, context)
    elif data.startswith("acc_detail:"):
        pid=data.split(":",1)[1]
        await show_account_detail(update, context, pid)
    elif data.startswith("acc_connect:"):
        pid=data.split(":",1)[1]
        if pid=="telegram_user":
            context.user_data["awaiting_phone"]=True
            await query.edit_message_text(
                "📱 <b>Подключение Telegram личного аккаунта</b>\n\nВведите номер телефона в формате <code>+380123456789</code>:\n\nСессия будет сохранена в <code>data/sessions/{user_id}.session</code> и не попадёт в Git.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="go_accounts")]]), parse_mode="HTML"
            )
        else:
            await query.edit_message_text(f"Для {pid} добавьте токены в .env и нажмите Проверить.\nСм. инструкции выше.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="go_accounts")]]))
    elif data.startswith("acc_disconnect:"):
        pid=data.split(":",1)[1]
        user_id=update.effective_user.id
        # Удаляем сессию
        if pid=="telegram_user":
            from pathlib import Path
            sess=Path(f"./data/sessions/{user_id}.session")
            if sess.exists():
                sess.unlink()
                # также удаляем запись в БД
                try:
                    from app.storage.repositories import ProviderConnectionRepo
                    from app.domain.models import ProviderConnection
                    repo=ProviderConnectionRepo(DATABASE_PATH)
                    await repo.upsert(ProviderConnection(owner_id=user_id, provider="telegram_user", status="not_connected", meta="Отключён пользователем"))
                except:
                    pass
                await query.edit_message_text("✅ Личный аккаунт отключён, сессия удалена.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="go_accounts")]]))
            else:
                await query.edit_message_text("Сессия не найдена.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="go_accounts")]]))
        else:
            await query.edit_message_text("Отключите, удалив токен из .env и перезапустив.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="go_accounts")]]))

async def handle_accounts_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_phone"):
        phone=update.message.text.strip()
        if not phone.startswith("+") or len(phone)<10:
            await update.message.reply_text("Неверный формат. Пример: +380123456789")
            return True
        user_id=update.effective_user.id
        context.user_data["phone"]=phone
        context.user_data.pop("awaiting_phone",None)
        context.user_data["awaiting_code"]=True
        await update.message.reply_text(
            f"Номер {phone} сохранён. Для реальной авторизации требуется Telethon и API_ID/HASH.\n\n"
            "В тестовом окружении сессия не создаётся, но flow сохранён.\n"
            "Введите код из Telegram (в демо любой 5-значный):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="go_accounts")]])
        )
        # В реальном — здесь бы вызывался TelegramClient.send_code_request
        # Но без API_ID мы не можем, честно сообщаем
        await update.message.reply_text("⚠️ Внимание: TELEGRAM_API_ID/HASH не настроены — подключение не завершено. Добавьте их в .env и повторите.")
        return True
    if context.user_data.get("awaiting_code"):
        code=update.message.text.strip()
        if len(code)<4:
            await update.message.reply_text("Код слишком короткий, попробуйте снова")
            return True
        context.user_data.pop("awaiting_code",None)
        context.user_data["awaiting_2fa"]=False
        await update.message.reply_text(f"Код {code[:2]}*** принят (демо). Если включен 2FA — введите пароль, иначе нажмите Готово.")
        await update.message.reply_text("Если 2FA не нужен — отправьте /done", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Готово", callback_data="go_accounts")]]))
        return True
    return False
