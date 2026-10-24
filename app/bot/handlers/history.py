from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from app.config import DATABASE_PATH
from app.storage.repositories import ActivityRepo, DeliveryRepo, CampaignRepo

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    repo = ActivityRepo(DATABASE_PATH)
    events = await repo.list_by_owner(user_id, limit=30)
    if not events:
        text = "🕘 <b>История</b> пуста.\n\nСобытия появятся после создания и запуска кампаний."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="go_menu")]])
    else:
        lines = []
        for e in events[:20]:
            camp = f"#{e.campaign_id}" if e.campaign_id else "—"
            lines.append(f"• {e.created_at[:19]} | {e.event} | камп. {camp} | {e.details[:60]}")
        text = "🕘 <b>История (последние 20):</b>\n\n" + "\n".join(lines) + f"\n\nВсего событий: {len(events)}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("📊 Отчёты", callback_data="go_reports")], [InlineKeyboardButton("🏠 Главное меню", callback_data="go_menu")]])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

async def show_reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    camp_repo = CampaignRepo(DATABASE_PATH)
    campaigns = await camp_repo.list_by_owner(user_id, limit=50)
    if not campaigns:
        text = "📊 <b>Отчёты</b>\n\nНет кампаний. Создайте кампанию, чтобы увидеть отчёты."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="go_menu")]])
    else:
        text = "📊 <b>Отчёты по кампаниям</b>\n\nПо каждой кампании: запланировано → отправлено API → доставлено/ошибка → пропущено политикой → ожидает повтора.\n<i>Числа берутся только из реальных статусов доставки, не из попыток.</i>\n\n"
        delivery_repo = DeliveryRepo(DATABASE_PATH)
        for c in campaigns[:10]:
            stats = await delivery_repo.stats(c.id)
            if stats:
                stats_str = ", ".join([f"{k}={v}" for k,v in stats.items()])
            else:
                if c.status in ("draft","needs_setup","ready"):
                    stats_str = f"не запущена (статус: {c.status})"
                else:
                    stats_str = "нет доставок (0 получателей или не в очереди)"
            text += f"#{c.id} · {c.platform} · {c.status}: {stats_str}\n"
            # also show honest limit vs actual
            text += f"   лимит кампании: {c.requested_limit} | ⚠️ реальный размер аудитории определяется согласием\n"
        if len(campaigns) > 10:
            text += f"\n... и ещё {len(campaigns)-10} кампаний в «📋 Мои кампании»"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🕘 История", callback_data="go_history")], [InlineKeyboardButton("🏠 Главное меню", callback_data="go_menu")]])
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            await update.callback_query.message.reply_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")
