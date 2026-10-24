from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from app.config import DATABASE_PATH

TEMPLATES = [
    {"id": "greeting", "name": "Приветствие", "text": "Привет, {name}! Рады видеть вас."},
    {"id": "promo", "name": "Акция", "text": "🔥 Специальное предложение для вас: {offer} — успейте до {date}!"},
    {"id": "reminder", "name": "Напоминание", "text": "Напоминаем: ваша запись {event} состоится {date}."},
]

async def show_templates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text="📄 <b>Шаблоны сообщений</b>\n━━━━━━━━━━━━━━━\nИспользуйте переменные {name}, {offer}, {date}, {event}. При отправке они заменятся.\n\n"
    kb=[]
    for t in TEMPLATES:
        text+=f"• <b>{t['name']}</b> — {t['text'][:60]}...\n"
        kb.append([InlineKeyboardButton(f"📋 {t['name']}", callback_data=f"tpl_use:{t['id']}")])
    kb.append([InlineKeyboardButton("🏠 Главное меню", callback_data="go_menu")])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def handle_templates_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query
    await query.answer()
    data=query.data
    if data.startswith("tpl_use:"):
        tid=data.split(":",1)[1]
        tpl=next((t for t in TEMPLATES if t["id"]==tid), None)
        if tpl:
            await query.edit_message_text(f"📋 <b>{tpl['name']}</b>\n\n<code>{tpl['text']}</code>\n\nСкопируйте и используйте в мастере кампании (шаг Текст).", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="go_templates")]]), parse_mode="HTML")
    elif data=="go_templates":
        await show_templates(update, context)
