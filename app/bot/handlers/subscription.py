from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from app.config import DATABASE_PATH, is_admin
from app.services.subscription_service import SubscriptionService
from app.services.payment_service import PaymentService
from app.storage.repositories import PaymentRequestRepo
from app.bot.keyboards import subscription_main_keyboard, subscription_offer_keyboard, payment_confirm_keyboard, admin_payment_keyboard
import html

async def show_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sub = SubscriptionService(DATABASE_PATH)
    pay = PaymentService(DATABASE_PATH)
    u = await sub.get_status(user_id)
    cfg = pay.get_config()
    has_pending = await pay.repo.has_pending(user_id)
    has_active = u.subscription_status == "active" and u.subscription_expires_at and _is_active(u)

    if has_active:
        text = (
            f"💎 <b>Подписка активна</b>\n\n"
            f"{sub.format_profile(u)}\n"
            f"✅ Вы можете запускать рассылки без ограничений до {u.subscription_expires_at[:10] if u.subscription_expires_at else '—'}.\n"
        )
        kb = subscription_main_keyboard(True, has_pending)
    else:
        remaining = max(0, u.free_total - u.free_used)
        if u.free_used >= u.free_total:
            # оффер
            text = pay.format_subscription_end_screen(u.free_used, u.free_total)
            kb = subscription_offer_keyboard()
        else:
            text = (
                f"💎 <b>Подписка — ${cfg['price']}/мес</b>\n\n"
                f"{sub.format_profile(u)}\n"
                f"Осталось бесплатных: <b>{remaining}</b>\n\n"
                f"Включает все каналы, историю и экспорт.\n"
                f"После исчерпания — оформление подписки $1 на {cfg['period_days']} дней.\n"
            )
            kb = subscription_main_keyboard(False, has_pending)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

def _is_active(u):
    if not u.subscription_expires_at:
        return False
    try:
        from datetime import datetime, timezone
        exp = datetime.fromisoformat(u.subscription_expires_at)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) <= exp
    except:
        return False

async def show_terms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📋 <b>Условия подписки</b>\n\n"
        "• Стоимость: <b>$1 / 30 дней</b>\n"
        "• Бесплатно: 10 рассылок для новых пользователей\n"
        "• Одна кампания = одна рассылка независимо от количества получателей\n"
        "• Черновики, ошибки и отмены не списывают лимит\n"
        "• Повторный запуск той же выполненной кампании не списывает повторно\n"
        "• Подписка активируется вручную админом после проверки оплаты\n"
        "• Автоматическое списание пока не реализовано (заглушка manual_placeholder)\n"
        "• Просмотр кампаний/статистики доступен без подписки\n"
        "• Токены и платежные данные не логируются\n"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("💳 Оформить", callback_data="sub_buy")], [InlineKeyboardButton("🏠 Меню", callback_data="go_menu")]])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

async def show_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pay = PaymentService(DATABASE_PATH)
    text = pay.format_offer()
    cfg = pay.get_config()
    if not cfg["is_configured"]:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Меню", callback_data="go_menu")]])
    else:
        kb = payment_confirm_keyboard()
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

async def handle_paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    pay = PaymentService(DATABASE_PATH)
    ok, msg, pr = await pay.create_request(user_id)
    if not ok:
        await update.callback_query.edit_message_text(f"⚠️ {msg}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Меню", callback_data="go_menu")]]))
        return
    text = (
        f"✅ <b>Заявка #{pr.id} создана</b>\n\n"
        f"Сумма: ${pr.amount_usd} на {pr.period_days} дней\n"
        f"Статус: <b>На рассмотрении</b>\n\n"
        f"Администратор проверит оплату вручную и активирует подписку.\n"
        f"Вы получите уведомление. До подтверждения подписка не активна.\n"
    )
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📜 Мои заявки", callback_data="sub_history")], [InlineKeyboardButton("🏠 Меню", callback_data="go_menu")]]), parse_mode="HTML")

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    pay = PaymentService(DATABASE_PATH)
    reqs = await pay.repo.list_by_user(user_id)
    if not reqs:
        text = "📜 У вас пока нет заявок на подписку."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("💳 Оформить", callback_data="sub_buy")], [InlineKeyboardButton("🏠 Меню", callback_data="go_menu")]])
    else:
        lines = []
        for r in reqs[:10]:
            lines.append(f"• #{r.id} — ${r.amount_usd} — {r.status} — {r.created_at[:10]}")
        text = "📜 <b>Мои заявки</b>\n\n" + "\n".join(lines)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Обновить", callback_data="sub_history")], [InlineKeyboardButton("🏠 Меню", callback_data="go_menu")]])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

async def show_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_subscription(update, context)

async def handle_admin_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.callback_query.edit_message_text("❌ Только администратор может просматривать заявки.")
        return
    pay = PaymentService(DATABASE_PATH)
    pending = await pay.list_pending()
    if not pending:
        text = "✅ Нет заявок на рассмотрении."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Меню", callback_data="go_menu")]])
    else:
        text = "👮 <b>Заявки на подписку (pending)</b>\n\n"
        for r in pending[:10]:
            text += f"• Заявка #{r.id} от {r.user_id} — ${r.amount_usd} — {r.created_at[:16]}\n"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"✅ #{r.id} Approve", callback_data=f"admin_approve:{r.id}") ] for r in pending[:5]] +
                                  [[InlineKeyboardButton(f"❌ #{r.id} Reject", callback_data=f"admin_reject:{r.id}")] for r in pending[:5]] +
                                  [[InlineKeyboardButton("🏠 Меню", callback_data="go_menu")]])
    await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")

async def handle_admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE, request_id: int):
    admin_id = update.effective_user.id
    if not is_admin(admin_id):
        await update.callback_query.edit_message_text("❌ Нет прав администратора.")
        return
    pay = PaymentService(DATABASE_PATH)
    ok, msg = await pay.approve(request_id, admin_id)
    if ok:
        # уведомить пользователя если возможно — отправим сообщение через bot? Пока просто логируем
        await update.callback_query.edit_message_text(f"✅ {msg}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 Остальные", callback_data="admin_payments")]]))
    else:
        await update.callback_query.edit_message_text(f"❌ {msg}")

async def handle_admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE, request_id: int):
    admin_id = update.effective_user.id
    if not is_admin(admin_id):
        await update.callback_query.edit_message_text("❌ Нет прав.")
        return
    pay = PaymentService(DATABASE_PATH)
    ok, msg = await pay.reject(request_id, admin_id, "Отклонено администратором")
    if ok:
        await update.callback_query.edit_message_text(f"✅ {msg}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 Остальные", callback_data="admin_payments")]]))
    else:
        await update.callback_query.edit_message_text(f"❌ {msg}")

async def handle_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    if data in ("go_subscription", "sub_status"):
        await show_subscription(update, context)
    elif data == "sub_buy":
        await show_buy(update, context)
    elif data == "sub_terms":
        await show_terms(update, context)
    elif data == "sub_paid":
        await handle_paid(update, context)
    elif data == "sub_history":
        await show_history(update, context)
    elif data == "sub_help":
        await show_terms(update, context)
    elif data.startswith("admin_approve:"):
        rid = int(data.split(":")[1])
        await handle_admin_approve(update, context, rid)
    elif data.startswith("admin_reject:"):
        rid = int(data.split(":")[1])
        await handle_admin_reject(update, context, rid)
    elif data == "admin_payments":
        await handle_admin_payments(update, context)
