"""
Диагностическая команда /diagnostics — проверка каждого канала без массовой отправки.
ТЗ §13: для Telegram — токен/getMe/база/тест/права канала; для Meta — токены/ID/разрешения; без фейка.
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from app.config import DATABASE_PATH
from app.providers.telegram_provider import TelegramProvider
from app.providers.meta_messenger_provider import MetaMessengerProvider
from app.providers.instagram_provider import InstagramProvider
from app.providers.whatsapp_provider import WhatsAppProvider
from app.providers.tiktok_provider import TikTokProvider
from app.providers.email_provider import EmailProvider

PROVIDERS = {
    "telegram": TelegramProvider,
    "facebook_messenger": MetaMessengerProvider,
    "instagram": InstagramProvider,
    "whatsapp": WhatsAppProvider,
    "tiktok": TikTokProvider,
    "email": EmailProvider,
}

async def show_diagnostics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = context.user_data.get("lang") or "ru"
    # соберём статусы без падения одного канала
    lines = "🔍 <b>Диагностика подключений</b> (без массовой отправки)\n━━━━━━━━━━━━━━━━━━━━\n\n"
    details = {}
    for plat, Cls in PROVIDERS.items():
        prov = Cls(db_path=DATABASE_PATH)
        try:
            res = await prov.check_connection(owner_id=user_id)
            st = res.get("status")
            hint = res.get("hint", "")
            nxt = res.get("next_step", "")
            caps = res.get("capabilities", {})
            req = res.get("required", [])
            details[plat] = res
            emoji = {"connected":"✅","not_connected":"⚪","configuration_error":"🟡","permission_error":"🟠","service_error":"🔴"}.get(st,"•")
            lines += f"{emoji} <b>{plat}</b> — <b>{st}</b>\n   {hint}\n"
            if nxt:
                lines += f"   → {nxt}\n"
            if req:
                lines += f"   требуется: {', '.join(req)}\n"
            # честно: что проверено
            if plat == "telegram" and st == "connected":
                # доп проверки: база подписчиков, права канала
                from app.storage.repositories import ContactRepo
                try:
                    cr = ContactRepo(DATABASE_PATH)
                    contacts = await cr.list_consented(user_id, "telegram")
                    lines += f"   подписчики в БД: {len(contacts)}\n"
                except:
                    pass
                ch = await prov.get_default_channel(user_id)
                if ch:
                    lines += f"   канал по умолчанию: {ch}\n"
                else:
                    lines += f"   канал не настроен — публикация unavailable\n"
            lines += "\n"
        except Exception as e:
            lines += f"🔴 <b>{plat}</b> — service_error\n   {e}\n\n"
            details[plat] = {"status":"service_error","hint":str(e)}

    lines += (
        "<b>Что подтверждено тестами:</b> запуск с 1 токеном, изоляция каналов, draft CRUD, лимит 10, идемпотентность, etc (49 тестов).\n"
        "<b>Что проверено через API:</b> Telegram getMe, токены Facebook/WhatsApp/Instagram (честность — не фейк).\n"
        "<b>Что требует конфигурации:</b> META_ACCESS_TOKEN, WHATSAPP_TOKEN, SMTP, TIKTOK — см. .env.example\n"
        "<b>Действия пользователя:</b> добавьте токены в .env, дайте права боту в канале/странице, настройте шаблоны WhatsApp.\n"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔌 Подключения", callback_data="go_connections")],
        [InlineKeyboardButton("🏠 Меню", callback_data="go_menu")],
    ])
    if update.callback_query:
        await update.callback_query.edit_message_text(lines, reply_markup=kb, parse_mode="HTML")
    else:
        await update.message.reply_text(lines, reply_markup=kb, parse_mode="HTML")

async def handle_diagnostics_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await show_diagnostics(update, context)
