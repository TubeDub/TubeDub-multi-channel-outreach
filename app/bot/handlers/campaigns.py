from telegram import Update
from telegram.ext import ContextTypes
from app.config import DATABASE_PATH
from app.bot.keyboards import *
from app.domain.statuses import CampaignStatus, Platform, CampaignType, AudienceSource, AudienceMode
from app.services.campaign_service import CampaignService
from app.services.validation_service import validate_url, validate_country_city
from app.storage.repositories import CampaignRepo, DeliveryRepo, ActivityRepo
from app.observability.logging_config import get_logger

logger = get_logger(__name__)

def _status_line(c):
    return f"{CampaignStatus.emoji(c.status)} {CampaignStatus.display(c.status)}"

def _campaign_details_text(c, deliveries_stats=None, activities=None):
    stats_str = ""
    if deliveries_stats is not None:
        if deliveries_stats:
            stats_str = "\n<b>Статистика отправок:</b> " + ", ".join([f"{k}: {v}" for k,v in deliveries_stats.items()])
        else:
            stats_str = "\n<b>Статистика:</b> пока нет отправок"
    geo = f"{c.country}{', '+c.city if c.city else ''}" or "—"
    link_str = c.link or "—"
    text_preview = (c.message_text[:400] + "...") if len(c.message_text) > 400 else c.message_text
    return (
        f"<b>📋 Кампания #{c.id}</b>\n\n"
        f"<b>Канал:</b> {Platform.display(c.platform)}\n"
        f"<b>Тип:</b> {CampaignType.display(c.campaign_type)}\n"
        f"<b>География:</b> {geo}\n"
        f"<i>ℹ️ География — параметр таргетинга, не список контактов</i>\n"
        f"<b>Источник:</b> {AudienceSource.display(c.audience_source)}\n"
        f"<b>Сегмент:</b> {AudienceMode.display(c.audience_mode)}\n"
        f"<b>Лимит (цель):</b> {c.requested_limit} | <i>Не рассчитано — будет определено платформой/наличием согласия</i>\n"
        f"<b>Текст:</b>\n{text_preview}\n"
        f"<b>Ссылка:</b> {link_str}\n"
        f"<b>Статус:</b> {_status_line(c)}\n"
        f"<b>Создана:</b> {c.created_at}\n"
        f"<b>Обновлена:</b> {c.updated_at}"
        f"{stats_str}\n"
    )

async def list_campaigns(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1):
    user_id = update.effective_user.id
    service = CampaignService(DATABASE_PATH)
    items, total, total_pages = await service.list_paginated(user_id, page=page, per_page=5)
    if total == 0:
        text = "📋 У вас пока нет кампаний.\n\nНажмите «➕ Создать кампанию» чтобы создать первую."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="go_menu")]])
    else:
        text = f"📋 <b>Мои кампании</b> — {total} шт., стр. {page}/{total_pages}\n\nКаждая строка — отдельная кампания. Нажмите чтобы открыть карточку."
        kb = campaign_list_keyboard(items, page, total_pages)

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            await update.callback_query.message.reply_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

async def open_campaign_card(update: Update, context: ContextTypes.DEFAULT_TYPE, campaign_id: int):
    user_id = update.effective_user.id
    service = CampaignService(DATABASE_PATH)
    try:
        c = await service.get_owned(campaign_id, user_id)
    except Exception as e:
        await update.callback_query.edit_message_text(f"❌ {e}")
        return
    delivery_repo = DeliveryRepo(DATABASE_PATH)
    stats = await delivery_repo.stats(c.id)
    text = _campaign_details_text(c, deliveries_stats=stats)
    kb = campaign_card_keyboard(c)
    await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")

async def view_campaign_details(update: Update, context: ContextTypes.DEFAULT_TYPE, campaign_id: int):
    user_id = update.effective_user.id
    service = CampaignService(DATABASE_PATH)
    try:
        c = await service.get_owned(campaign_id, user_id)
    except Exception as e:
        await update.callback_query.edit_message_text(f"❌ {e}")
        return
    delivery_repo = DeliveryRepo(DATABASE_PATH)
    activity_repo = ActivityRepo(DATABASE_PATH)
    stats = await delivery_repo.stats(c.id)
    activities = await activity_repo.list_by_campaign(c.id)
    hist = ""
    if activities:
        hist = "\n\n<b>Последние события:</b>\n" + "\n".join([f"• {a.created_at} — {a.event}: {a.details}" for a in activities[:10]])
    text = _campaign_details_text(c, deliveries_stats=stats) + hist
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад к карточке", callback_data=f"camp_open:{c.id}")],
        [InlineKeyboardButton("⬅️ К списку", callback_data="camp_list:1"), InlineKeyboardButton("🏠 Главное меню", callback_data="go_menu")],
    ])
    await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")

async def duplicate_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE, campaign_id: int):
    user_id = update.effective_user.id
    service = CampaignService(DATABASE_PATH)
    try:
        copy = await service.duplicate(campaign_id, user_id)
        await update.callback_query.edit_message_text(
            f"✅ Создана копия #{copy.id} из #{campaign_id}\nСтатус: Черновик (копия).\nОткройте карточку для редактирования.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 Открыть копию", callback_data=f"camp_open:{copy.id}")], [InlineKeyboardButton("⬅️ К списку", callback_data="camp_list:1")]]),
            parse_mode="HTML"
        )
    except Exception as e:
        await update.callback_query.edit_message_text(f"❌ Ошибка дублирования: {e}")

async def edit_campaign_start(update: Update, context: ContextTypes.DEFAULT_TYPE, campaign_id: int):
    user_id = update.effective_user.id
    service = CampaignService(DATABASE_PATH)
    try:
        c = await service.get_owned(campaign_id, user_id)
    except Exception as e:
        await update.callback_query.edit_message_text(f"❌ {e}")
        return
    if c.status in ("queued", "running"):
        await update.callback_query.edit_message_text(f"⚠️ Кампания #{c.id} выполняется — редактирование заблокировано. Сначала отмените.")
        return
    text = f"✏️ <b>Редактирование #{c.id}</b>\n\nЧто изменить?"
    kb = edit_choice_keyboard(c.id)
    await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")

async def edit_field_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, campaign_id: int, field: str):
    context.user_data["edit_state"] = {"campaign_id": campaign_id, "field": field}
    prompts = {
        "text": "Введите новый текст сообщения (5–4096 символов):",
        "link": "Введите новую ссылку (https://...) или '-' чтобы удалить:",
        "geo": "Введите страну и город через запятую, например: Украина, Киев\nИли только страну: Германия\nИли '-' для очистки города (оставит страну)",
        "limit": "Введите новый лимит 1–10000:",
    }
    await update.callback_query.edit_message_text(prompts.get(field, "Введите значение:"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data=f"camp_open:{campaign_id}")]]))

async def handle_edit_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("edit_state")
    if not state:
        return
    text = update.message.text.strip()
    campaign_id = state["campaign_id"]
    field = state["field"]
    user_id = update.effective_user.id
    service = CampaignService(DATABASE_PATH)
    try:
        if field == "text":
            if len(text) < 5:
                await update.message.reply_text("Текст слишком короткий (мин 5). Попробуйте снова:")
                return
            if len(text) > 4096:
                await update.message.reply_text("Текст слишком длинный (макс 4096). Сократите:")
                return
            await service.update(campaign_id, user_id, message_text=text)
        elif field == "link":
            if text == "-":
                await service.update(campaign_id, user_id, link="")
            else:
                ok, msg = validate_url(text)
                if not ok:
                    await update.message.reply_text(f"⚠️ {msg}\nПопробуйте снова или '-' чтобы удалить:")
                    return
                await service.update(campaign_id, user_id, link=text)
        elif field == "geo":
            # parse country, city
            if "," in text:
                parts = [p.strip() for p in text.split(",",1)]
                country, city = parts[0], parts[1] if parts[1] != "-" else ""
            else:
                if text == "-":
                    country, city = "", ""
                else:
                    country, city = text, ""
            ok, msg = validate_country_city(country or "x", city)
            if not ok and country:
                await update.message.reply_text(f"⚠️ {msg}\nПример: Украина, Киев")
                return
            # Need to fetch current to keep city if only country
            c = await service.get_owned(campaign_id, user_id)
            if not country:
                # just update city?
                await service.update(campaign_id, user_id, city=city)
            else:
                await service.update(campaign_id, user_id, country=country, city=city)
        elif field == "limit":
            try:
                num = int(text)
                if num < 1 or num > 10000:
                    await update.message.reply_text("Лимит 1–10000:")
                    return
                await service.update(campaign_id, user_id, requested_limit=num)
            except ValueError:
                await update.message.reply_text("Введите число 1–10000:")
                return
        context.user_data.pop("edit_state", None)
        c = await service.get_owned(campaign_id, user_id)
        kb = campaign_card_keyboard(c)
        await update.message.reply_text(f"✅ Кампания #{c.id} обновлена.", reply_markup=kb, parse_mode="HTML")
        # also show card again as new message
        stats = await DeliveryRepo(DATABASE_PATH).stats(c.id)
        await update.message.reply_text(_campaign_details_text(c, stats), reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка редактирования: {e}")

async def delete_campaign_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, campaign_id: int):
    await update.callback_query.edit_message_text(
        f"⚠️ Удалить кампанию #{campaign_id}?\nЭто действие нельзя отменить. История других кампаний не пострадает.",
        reply_markup=confirm_delete_keyboard(campaign_id)
    )

async def delete_campaign_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, campaign_id: int):
    user_id = update.effective_user.id
    service = CampaignService(DATABASE_PATH)
    try:
        await service.delete(campaign_id, user_id)
        await update.callback_query.edit_message_text(f"✅ Кампания #{campaign_id} удалена.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ К списку", callback_data="camp_list:1")]]))
    except Exception as e:
        await update.callback_query.edit_message_text(f"❌ Не удалось удалить: {e}")

async def run_campaign_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, campaign_id: int):
    user_id = update.effective_user.id
    service = CampaignService(DATABASE_PATH)
    try:
        c = await service.get_owned(campaign_id, user_id)
    except Exception as e:
        await update.callback_query.edit_message_text(f"❌ {e}")
        return
    # readiness check
    from app.providers.telegram_provider import TelegramProvider
    from app.providers.telegram_user_provider import TelegramUserProvider
    from app.providers.meta_messenger_provider import MetaMessengerProvider
    from app.providers.instagram_provider import InstagramProvider
    from app.providers.whatsapp_provider import WhatsAppProvider
    from app.providers.tiktok_provider import TikTokProvider
    from app.providers.email_provider import EmailProvider
    providers = {
        "telegram_user": TelegramUserProvider(db_path=DATABASE_PATH),
        "telegram": TelegramProvider(db_path=DATABASE_PATH),
        "facebook_messenger": MetaMessengerProvider(db_path=DATABASE_PATH),
        "instagram": InstagramProvider(db_path=DATABASE_PATH),
        "whatsapp": WhatsAppProvider(db_path=DATABASE_PATH),
        "tiktok": TikTokProvider(db_path=DATABASE_PATH),
        "email": EmailProvider(db_path=DATABASE_PATH),
    }
    async def checker(platform, owner_id):
        try:
            return await providers[platform].check_connection(owner_id)
        except Exception as e:
            return {"status": "not_connected", "hint": str(e)}
    ok, reasons = await service.check_readiness(campaign_id, user_id, checker)
    # Проверка подписки / лимита
    from app.services.subscription_service import SubscriptionService
    sub = SubscriptionService(DATABASE_PATH)
    can, sub_msg = await sub.can_send(user_id)
    if not can:
        reasons.append(sub_msg + " — 💎 Подписка $1/мес, см. 💎 Подписка")
        ok = False
    if not ok:
        text = f"⚠️ Кампанию #{c.id} нельзя запустить:\\n\\n• " + "\\n• ".join(reasons) + "\\n\\nИсправьте в редактировании или подключите канал в «🔌 Подключения»."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✏️ Редактировать", callback_data=f"camp_edit:{c.id}")], [InlineKeyboardButton("💎 Подписка", callback_data="go_subscription")], [InlineKeyboardButton("⬅️ Назад", callback_data=f"camp_open:{c.id}")]])
        await update.callback_query.edit_message_text(text, reply_markup=kb)
        return
    # show confirm
    text = (
        f"<b>Подтвердите запуск #{c.id}</b>\n\n"
        f"Канал: {Platform.display(c.platform)}\n"
        f"Тип: {CampaignType.display(c.campaign_type)}\n"
        f"География: {c.country}{', '+c.city if c.city else ''}\n"
        f"Аудитория: {AudienceSource.display(c.audience_source)} · лимит {c.requested_limit}\n\n"
        f"Будет выполнена реальная отправка/публикация через официальный API.\n"
        f"Подтвердите только если аудитория дала согласие и права в канале выданы."
    )
    await update.callback_query.edit_message_text(text, reply_markup=confirm_run_keyboard(c.id), parse_mode="HTML")

async def run_campaign_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, campaign_id: int):
    user_id = update.effective_user.id
    service = CampaignService(DATABASE_PATH)
    # idempotency: generate key
    import uuid
    key = str(uuid.uuid4())
    # Prevent double-run if already queued/running
    try:
        c = await service.get_owned(campaign_id, user_id)
        if c.status in ("queued", "running"):
            await update.callback_query.edit_message_text(f"⚠️ Кампания #{c.id} уже в очереди/выполняется. Повторный запуск не создан.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ К карточке", callback_data=f"camp_open:{c.id}")]]))
            return
        # set queued
        await service.set_status(campaign_id, user_id, "queued", idempotency_key=key)
        await update.callback_query.edit_message_text(f"⏳ Кампания #{campaign_id} поставлена в очередь. Запуск выполняется...", parse_mode="HTML")
        # dispatch
        from app.providers.telegram_provider import TelegramProvider
        from app.providers.telegram_user_provider import TelegramUserProvider
        from app.providers.meta_messenger_provider import MetaMessengerProvider
        from app.providers.instagram_provider import InstagramProvider
        from app.providers.whatsapp_provider import WhatsAppProvider
        from app.providers.tiktok_provider import TikTokProvider
        from app.providers.email_provider import EmailProvider
        from app.services.delivery_service import DeliveryService
        from app.workers.dispatcher import Dispatcher

        providers = {
        "telegram_user": TelegramUserProvider(db_path=DATABASE_PATH),
        "telegram": TelegramProvider(db_path=DATABASE_PATH),
        "facebook_messenger": MetaMessengerProvider(db_path=DATABASE_PATH),
        "instagram": InstagramProvider(db_path=DATABASE_PATH),
        "whatsapp": WhatsAppProvider(db_path=DATABASE_PATH),
        "tiktok": TikTokProvider(db_path=DATABASE_PATH),
        "email": EmailProvider(db_path=DATABASE_PATH),
        }
        delivery_service = DeliveryService(DATABASE_PATH, providers)
        dispatcher = Dispatcher(DATABASE_PATH, delivery_service)
        # run in background without blocking callback edit too long? For simplicity, await but with timeout? We'll run and update afterwards
        await dispatcher.dispatch_one(campaign_id, user_id)
        # after completion, fetch new status
        repo = CampaignRepo(DATABASE_PATH)
        final = await repo.get(campaign_id)
        stats = await DeliveryRepo(DATABASE_PATH).stats(campaign_id)
        status_text = CampaignStatus.display(final.status) if final else "неизвестно"
        stats_str = ", ".join([f"{k}: {v}" for k,v in stats.items()]) if stats else "нет отправок"
        from app.services.subscription_service import SubscriptionService as SS
        ss = SS(DATABASE_PATH)
        u = await ss.get_status(user_id)
        sub_info = f"\n🎁 Осталось бесплатных: {max(0, u.free_total - u.free_used)}/{u.free_total}"
        result_text = (
            f"🏁 <b>Результат кампании #{campaign_id}</b>\n\n"
            f"Статус: <b>{status_text}</b>\n"
            f"Статистика: {stats_str}{sub_info}\n\n"
        )
        if final.status == "completed":
            result_text += "✅ Запуск выполнен. Сообщения подтверждены API."
        elif final.status == "failed":
            result_text += "❌ Запуск завершился с ошибками. См. историю для деталей."
        elif final.status == "cancelled":
            result_text += "🛑 Кампания отменена."
        else:
            result_text += f"Текущий статус: {status_text}"

        await update.callback_query.edit_message_text(result_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 К карточке", callback_data=f"camp_open:{campaign_id}")], [InlineKeyboardButton("⬅️ К списку", callback_data="camp_list:1")]]), parse_mode="HTML")

    except Exception as e:
        logger.exception(f"run confirm error: {e}")
        await update.callback_query.edit_message_text(f"❌ Ошибка запуска: {e}")

async def pause_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE, campaign_id: int):
    user_id = update.effective_user.id
    service = CampaignService(DATABASE_PATH)
    try:
        await service.set_status(campaign_id, user_id, "paused")
        await update.callback_query.edit_message_text(f"⏸ Кампания #{campaign_id} приостановлена.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("▶️ Возобновить", callback_data=f"camp_resume:{campaign_id}")], [InlineKeyboardButton("⬅️ К карточке", callback_data=f"camp_open:{campaign_id}")]]))
    except Exception as e:
        await update.callback_query.edit_message_text(f"❌ {e}")

async def resume_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE, campaign_id: int):
    user_id = update.effective_user.id
    service = CampaignService(DATABASE_PATH)
    try:
        await service.set_status(campaign_id, user_id, "queued")
        # also need to set to running and resume dispatcher? Simplified: set to queued then trigger dispatcher
        from app.providers.telegram_provider import TelegramProvider
        from app.providers.telegram_user_provider import TelegramUserProvider
        from app.providers.meta_messenger_provider import MetaMessengerProvider
        from app.providers.instagram_provider import InstagramProvider
        from app.providers.whatsapp_provider import WhatsAppProvider
        from app.providers.tiktok_provider import TikTokProvider
        from app.providers.email_provider import EmailProvider
        from app.services.delivery_service import DeliveryService
        from app.workers.dispatcher import Dispatcher
        providers = {
        "telegram_user": TelegramUserProvider(db_path=DATABASE_PATH),
        "telegram": TelegramProvider(db_path=DATABASE_PATH),
        "facebook_messenger": MetaMessengerProvider(db_path=DATABASE_PATH),
        "instagram": InstagramProvider(db_path=DATABASE_PATH),
        "whatsapp": WhatsAppProvider(db_path=DATABASE_PATH),
        "tiktok": TikTokProvider(db_path=DATABASE_PATH),
        "email": EmailProvider(db_path=DATABASE_PATH),
        }
        delivery_service = DeliveryService(DATABASE_PATH, providers)
        dispatcher = Dispatcher(DATABASE_PATH, delivery_service)
        await update.callback_query.edit_message_text(f"▶️ Кампания #{campaign_id} возобновлена...")
        await dispatcher.dispatch_one(campaign_id, user_id)
        await update.callback_query.edit_message_text(f"✅ Кампания #{campaign_id} продолжена и завершена.")
    except Exception as e:
        await update.callback_query.edit_message_text(f"❌ {e}")

async def cancel_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE, campaign_id: int):
    user_id = update.effective_user.id
    service = CampaignService(DATABASE_PATH)
    try:
        await service.set_status(campaign_id, user_id, "cancelled")
        # also cancel delivery service tasks if any
        from app.providers.telegram_provider import TelegramProvider
        from app.providers.telegram_user_provider import TelegramUserProvider
        from app.providers.meta_messenger_provider import MetaMessengerProvider
        from app.providers.instagram_provider import InstagramProvider
        from app.providers.whatsapp_provider import WhatsAppProvider
        from app.providers.tiktok_provider import TikTokProvider
        from app.providers.email_provider import EmailProvider
        from app.services.delivery_service import DeliveryService
        delivery_service = DeliveryService(DATABASE_PATH, {
        "telegram_user": TelegramUserProvider(db_path=DATABASE_PATH),
        "telegram": TelegramProvider(db_path=DATABASE_PATH),
        "facebook_messenger": MetaMessengerProvider(db_path=DATABASE_PATH),
        "instagram": InstagramProvider(db_path=DATABASE_PATH),
        "whatsapp": WhatsAppProvider(db_path=DATABASE_PATH),
        "tiktok": TikTokProvider(db_path=DATABASE_PATH),
        "email": EmailProvider(db_path=DATABASE_PATH),
        })
        await delivery_service.cancel(campaign_id, user_id)
        await update.callback_query.edit_message_text(f"🛑 Кампания #{campaign_id} отменена.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ К карточке", callback_data=f"camp_open:{campaign_id}")]]))
    except Exception as e:
        await update.callback_query.edit_message_text(f"❌ {e}")

async def handle_campaign_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("camp_list:"):
        page = int(data.split(":")[1])
        await list_campaigns(update, context, page=page)
    elif data.startswith("camp_open:"):
        cid = int(data.split(":")[1])
        await open_campaign_card(update, context, cid)
    elif data.startswith("camp_view:"):
        cid = int(data.split(":")[1])
        await view_campaign_details(update, context, cid)
    elif data.startswith("camp_edit:"):
        cid = int(data.split(":")[1])
        await edit_campaign_start(update, context, cid)
    elif data.startswith("camp_edit_field:"):
        parts = data.split(":")
        cid = int(parts[1])
        field = parts[2]
        await edit_field_prompt(update, context, cid, field)
    elif data.startswith("camp_dup:"):
        cid = int(data.split(":")[1])
        await duplicate_campaign(update, context, cid)
    elif data.startswith("camp_del:"):
        cid = int(data.split(":")[1])
        await delete_campaign_prompt(update, context, cid)
    elif data.startswith("camp_del_confirm:"):
        cid = int(data.split(":")[1])
        await delete_campaign_confirm(update, context, cid)
    elif data.startswith("camp_run:"):
        cid = int(data.split(":")[1])
        await run_campaign_prompt(update, context, cid)
    elif data.startswith("camp_run_confirm:"):
        cid = int(data.split(":")[1])
        await run_campaign_confirm(update, context, cid)
    elif data.startswith("camp_pause:"):
        cid = int(data.split(":")[1])
        await pause_campaign(update, context, cid)
    elif data.startswith("camp_resume:"):
        cid = int(data.split(":")[1])
        await resume_campaign(update, context, cid)
    elif data.startswith("camp_cancel:"):
        cid = int(data.split(":")[1])
        await cancel_campaign(update, context, cid)
    elif data == "go_menu":
        from app.bot.keyboards import main_menu_keyboard
        await query.edit_message_text("🏠 Главное меню:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Открыть меню", callback_data="noop")]]))
        await query.message.reply_text("Выберите действие:", reply_markup=main_menu_keyboard())
