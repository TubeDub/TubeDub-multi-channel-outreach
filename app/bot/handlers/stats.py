from telegram import Update
from telegram.ext import ContextTypes
from app.config import DATABASE_PATH
from app.storage.repositories import CampaignRepo, DeliveryRepo, ActivityRepo
from app.services.subscription_service import SubscriptionService
from app.bot.keyboards import stats_keyboard

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else 0
    sub = SubscriptionService(DATABASE_PATH)
    u = await sub.get_status(user_id)
    camp_repo = CampaignRepo(DATABASE_PATH)
    campaigns = await camp_repo.list_by_owner(user_id, limit=50)
    total = len(campaigns)
    by_status = {}
    for c in campaigns:
        by_status[c.status] = by_status.get(c.status, 0) + 1

    delivery_repo = DeliveryRepo(DATABASE_PATH)
    total_selected = total_available = total_pending = total_sending = total_sent = total_delivered = total_failed = total_skipped = total_retry = total_cancelled = 0
    for c in campaigns[:20]:
        try:
            d = await delivery_repo.detailed_stats(c)
            total_selected += d.get("selected",0)
            total_available += d.get("available",0)
            total_pending += d.get("pending",0)
            total_sending += d.get("sending",0)
            total_sent += d.get("sent",0)
            total_delivered += d.get("delivered",0)
            total_failed += d.get("failed",0)
            total_skipped += d.get("skipped",0)
            total_retry += d.get("retry",0)
            total_cancelled += d.get("cancelled",0)
        except:
            stats = await delivery_repo.stats(c.id)
            total_sent += stats.get("sent",0)
            total_failed += stats.get("failed",0)
            total_skipped += stats.get("skipped",0)

    text = (
        f"📊 <b>Статистика — честные показатели</b>\n\n"
        f"👤 Пользователь: <code>{user_id}</code>\n"
        f"🎁 Бесплатно: {u.free_used}/{u.free_total} (осталось {max(0, u.free_total - u.free_used)})\n"
        f"💎 Подписка: {u.subscription_status} до {u.subscription_expires_at[:10] if u.subscription_expires_at else '—'}\n\n"
        f"📋 <b>Кампании:</b> всего {total}\n"
    )
    for st, cnt in by_status.items():
        from app.domain.statuses import CampaignStatus
        text += f"• {CampaignStatus.display(st)} ({st}): {cnt}\n"
    text += (
        f"\n📨 <b>Честная статистика (по сохранённым результатам API):</b>\n"
        f"• Выбрано получателей: {total_selected}\n"
        f"• Доступно для отправки: {total_available}\n"
        f"• Ожидает отправки: {total_pending}\n"
        f"• Отправляется: {total_sending}\n"
        f"• Успешно принято API: {total_sent}\n"
        f"• Доставлено (если канал подтверждает): {total_delivered}\n"
        f"• Ошибка отправки: {total_failed}\n"
        f"• Пропущено с причиной: {total_skipped}\n"
        f"• Ожидает повторной попытки: {total_retry}\n"
        f"• Отменено: {total_cancelled}\n"
        f"\n<i>Успех засчитывается только после подтверждённого ok от API. Завершена — когда все задания в финальном состоянии. Счётчики — по deliveries, не по заранее заданным числам.</i>\n"
    )
    if not campaigns:
        text += "\nСоздайте первую кампанию: 🚀 Создать кампанию"
    text += "\n<i>Просмотр доступен без подписки. Запуск новых — по лимиту/подписке.</i>"

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=stats_keyboard(), parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=stats_keyboard(), parse_mode="HTML")
