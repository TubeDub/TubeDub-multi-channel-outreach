from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from app.config import DATABASE_PATH
from app.services.subscription_service import SubscriptionService
from app.bot.keyboards import account_keyboard

async def show_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    svc = SubscriptionService(DATABASE_PATH)
    u = await svc.get_or_create_user(user.id, username=user.username or "", first_name=user.full_name or "")
    u = await svc.get_status(user.id)
    text = svc.format_profile(u)
    text += "\n\n<i>💡 Одна кампания = одна рассылка. Черновики не списывают лимит. Повторный запуск той же кампании не дублирует списание.</i>"
    kb = account_keyboard()
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

async def handle_account_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "go_account":
        await show_account(update, context)
