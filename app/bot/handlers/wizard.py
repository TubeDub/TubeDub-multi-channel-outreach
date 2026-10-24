from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from app.config import DATABASE_PATH
from app.bot.keyboards import *
from app.domain.statuses import Platform, CampaignType, AudienceSource
from app.domain.models import Campaign
from app.services.campaign_service import CampaignService
from app.services.validation_service import validate_url, validate_country_city
from app.observability.logging_config import get_logger
import json

logger = get_logger(__name__)

# 9 шагов — мастер кампаний §11 ТЗ
STEPS = ["platform", "campaign_type", "audience_source", "geography", "recipients", "message_text", "link", "preview", "schedule"]
STEP_TITLES = {
    "platform": "1/9 — Канал",
    "campaign_type": "2/9 — Тип кампании",
    "audience_source": "3/9 — Аудитория",
    "geography": "4/9 — География",
    "recipients": "5/9 — Получатели",
    "message_text": "6/9 — Текст сообщения",
    "link": "7/9 — Ссылка",
    "preview": "8/9 — Предпросмотр",
    "schedule": "9/9 — Запуск",
}

def _new_wizard():
    return {
        "step": 0,
        "data": {
            "platform": "telegram_user",
            "campaign_type": "audience_message",
            "country": "",
            "city": "",
            "audience_source": "bot_subscribers",
            "audience_mode": "subscribers",
            "requested_limit": 10,
            "recipients": [],
            "message_text": "",
            "link": "",
            "schedule": "draft",
        },
        "history": [],
    }

def _progress(step_idx: int) -> str:
    total = len(STEPS)
    pct = int((step_idx+1)/total*100)
    bar = "▓" * (step_idx+1) + "░" * (total-step_idx-1)
    return f"{bar} {pct}% — шаг {step_idx+1}/{total}"

async def _get_connections_for_wizard():
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
    statuses = {}
    for plat, prov in providers.items():
        try:
            res = await prov.check_connection(owner_id=0)
            statuses[plat] = res.get("status", "not_connected")
        except Exception:
            statuses[plat] = "service_error"
    return statuses

async def start_wizard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["wizard"] = _new_wizard()
    await _show_step(update, context, 0)

async def _show_step(update: Update, context: ContextTypes.DEFAULT_TYPE, step_idx: int):
    wizard = context.user_data.get("wizard")
    if not wizard:
        return
    wizard["step"] = step_idx
    step_name = STEPS[step_idx]
    progress = _progress(step_idx)
    send_func = None
    if update.callback_query:
        send_func = lambda text, kb, parse="HTML": update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode=parse)
    else:
        send_func = lambda text, kb, parse="HTML": update.message.reply_text(text, reply_markup=kb, parse_mode=parse)
    try:
        if step_name == "platform":
            conns = await _get_connections_for_wizard()
            text = (
                f"{progress}\n\n"
                f"<b>🚀 {STEP_TITLES[step_name]}: Выберите канал (отправителя)</b>\n"
                f"Где будет отправлено сообщение?\n\n"
                f"Статусы: ✅ Подключён · ⚪ Не подключён · 🟡 Ошибка конфигурации · 🟠 Нет разрешений · 🔴 Сервис недоступен\n"
                f"• <b>Telegram Личный</b> — от вашего имени (Telethon, сессия per user)\n"
                f"• <b>Telegram Бот</b> — от имени бота (Bot API, ограничен)\n"
                f"Черновик можно создать без подключения, отправка — только с подключением."
            )
            await send_func(text, platform_keyboard(conns))
        elif step_name == "campaign_type":
            plat = wizard["data"]["platform"]
            text = (
                f"{progress}\n\n"
                f"<b>{STEP_TITLES[step_name]}: Тип кампании</b>\n"
                f"Канал: <b>{Platform.display(plat)}</b>\n\n"
                f"Выберите тип — он влияет на проверку готовности и статистику:\n"
                f"• Публикация в канал/страницу — пост в ваш канал\n"
                f"• Сообщение аудитории — личная рассылка (цель до 100 успешных)\n"
                f"• Рекламная — для будущих интеграций Ads API\n"
            )
            await send_func(text, campaign_type_keyboard(plat))
        elif step_name == "audience_source":
            text = (
                f"{progress}\n\n"
                f"<b>{STEP_TITLES[step_name]}: Источник аудитории</b>\n"
                f"Откуда берём адресатов? Реальные адресаты только с согласием.\n"
                f"ℹ️ Неподключённый канал предложит черновик, не фейк-отправку."
            )
            await send_func(text, audience_source_keyboard())
        elif step_name == "geography":
            # Country picker substep
            from app.bot.handlers.pickers import build_country_picker
            lang = context.user_data.get("lang") or "ru"
            if "country_picker" not in context.user_data:
                context.user_data["country_picker"] = {"query":"", "page":0, "selected":[wizard["data"]["country"]] if wizard["data"]["country"] else [], "mode":"wizard"}
            picker = context.user_data["country_picker"]
            text, kb = build_country_picker(query=picker.get("query",""), page=picker.get("page",0), selected=picker.get("selected", []), lang=lang)
            # prepend progress
            text = f"{progress}\n\n<b>{STEP_TITLES[step_name]}: Страна и город</b>\nВыберите страну (поиск без Enter, учёт вариантов написания):\n\n" + text
            await send_func(text, kb)
        elif step_name == "recipients":
            cur = wizard["data"]["recipients"]
            cur_str = ", ".join(cur[:5]) + ("..." if len(cur)>5 else "") if cur else "— (будут взяты подписчики/импорт)"
            plat = wizard["data"]["platform"]
            text = (
                f"{progress}\n\n"
                f"<b>{STEP_TITLES[step_name]}: Получатели</b>\n"
                f"Текущие: {cur_str}\n"
                f"Канал {Platform.display(plat)}: введите реальные адресаты или оставьте пусто для аудиторий бота.\n"
                f"• Email — адреса через запятую\n"
                f"• WhatsApp/Messenger — телефоны/PSID\n"
                f"• Telegram личный — username/ID из ваших диалогов (не спам рандомным)\n"
                f"Отписавшиеся автоматически исключаются."
            )
            await send_func(text, recipients_keyboard())
        elif step_name == "message_text":
            text = (
                f"{progress}\n\n"
                f"<b>{STEP_TITLES[step_name]}: Текст сообщения</b>\n"
                f"Введите текст (5–4096 символов) с переменными {{name}} если нужно.\n"
                f"Шаблоны: используйте 📄 Шаблоны в меню для выборки."
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📄 Выбрать шаблон", callback_data="wiz_pick_template")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="wiz_back"), InlineKeyboardButton("❌ Отмена", callback_data="wiz_cancel")],
            ])
            await send_func(text, kb)
        elif step_name == "link":
            text = (
                f"{progress}\n\n"
                f"<b>{STEP_TITLES[step_name]}: Ссылка (опционально)</b>\n"
                f"Введите URL с https:// или «-» чтобы пропустить.\n"
                f"Пример: https://t.me/your_channel"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("⏭ Пропустить", callback_data="wiz_skip_link")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="wiz_back"), InlineKeyboardButton("❌ Отмена", callback_data="wiz_cancel")],
            ])
            await send_func(text, kb)
        elif step_name == "preview":
            d = wizard["data"]
            rec_str = ", ".join(d["recipients"][:5]) if d["recipients"] else f"{AudienceSource.display(d['audience_source'])} · {d['audience_mode']} · лимит {d['requested_limit']}"
            preview_text = d["message_text"][:600] + ("..." if len(d["message_text"])>600 else "")
            if d["link"]:
                preview_text += f"\n\n🔗 {d['link']}"
            text = (
                f"{progress}\n\n"
                f"<b>🔍 {STEP_TITLES[step_name]} — проверьте перед отправкой</b>\n\n"
                f"<b>Канал:</b> {Platform.display(d['platform'])} · {CampaignType.display(d['campaign_type'])}\n"
                f"<b>Гео:</b> {d['country'] or '—'}{', '+d['city'] if d['city'] else ''}\n"
                f"<b>Аудитория:</b> {AudienceSource.display(d['audience_source'])} · {d['audience_mode']}\n"
                f"<b>Получатели:</b> {rec_str}\n"
                f"<b>Текст:</b> {preview_text[:500]}\n"
                f"<b>Ссылка:</b> {d['link'] or '—'}\n\n"
                f"Это предпросмотр — реальная отправка покажет honest статистику (sent только после ok)."
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Всё верно", callback_data="wiz_to_schedule")],
                [InlineKeyboardButton("✏️ Изменить текст", callback_data="wiz_edit_text"), InlineKeyboardButton("🔗 Изменить ссылку", callback_data="wiz_edit_link")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="wiz_back"), InlineKeyboardButton("❌ Отмена", callback_data="wiz_cancel")],
            ])
            await send_func(text, kb)
        elif step_name == "schedule":
            # Показать статус лимитера перед запуском
            try:
                from app.services.account_rate_limiter import AccountRateLimiter
                lim = AccountRateLimiter(DATABASE_PATH)
                await lim.init()
                plat = wizard["data"]["platform"]
                status_msg = await lim.get_status_message(update.effective_user.id if update.effective_user else 0, plat)
            except Exception as e:
                status_msg = f"Статус лимитера: {e}"
            text = (
                f"{progress}\n\n"
                f"<b>{STEP_TITLES[step_name]}: Запуск</b>\n\n"
                f"📊 {status_msg}\n\n"
                f"• <b>Сохранить черновик</b> — можно запустить позже (пауза/рестарт/отмена)\n"
                f"• <b>Запустить сейчас</b> — проверка подключения, подписки (10 бесплатно → $1), лимитов, затем очередь\n"
                f"• Очередь постоянна в БД, цель до 100 успешных, пауза/продолжение без дублей\n"
                f"• При FloodWait/PeerFlood — автоматическая пауза и статус отложено/ограничен\n"
            )
            await send_func(text, schedule_keyboard())
    except Exception as e:
        logger.exception(f"wizard show step error: {e}")

async def handle_wizard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    wizard = context.user_data.get("wizard")
    if not wizard:
        await query.edit_message_text("Сессия истекла. Начните заново: 🚀 Создать кампанию")
        return
    cur_step = wizard["step"]
    if data == "wiz_cancel":
        context.user_data.pop("wizard", None)
        context.user_data.pop("country_picker", None)
        await query.edit_message_text("❌ Создание отменено. Черновик не создан.")
        from app.bot.keyboards import main_menu_keyboard
        lang = context.user_data.get("lang") or "ru"
        await query.message.reply_text("Выберите действие:", reply_markup=main_menu_keyboard(lang))
        return
    if data == "wiz_back":
        if cur_step > 0:
            await _show_step(update, context, cur_step-1)
        else:
            context.user_data.pop("wizard", None)
            await query.edit_message_text("❌ Отменено.")
        return
    if data == "wiz_skip_link":
        wizard["data"]["link"] = ""
        await _show_step(update, context, cur_step+1)
        return
    if data == "wiz_to_schedule":
        wizard["data"]["schedule"] = "now"
        await _show_step(update, context, cur_step+1)
        return
    if data == "wiz_pick_template":
        from app.bot.handlers.templates import show_templates
        await show_templates(update, context)
        # after pick, wizard stays; template handler will return
        return
    if data.startswith("wiz_platform:"):
        plat = data.split(":",1)[1]
        wizard["data"]["platform"] = plat
        await _show_step(update, context, cur_step+1)
        return
    if data.startswith("wiz_ctype:"):
        ct = data.split(":",1)[1]
        wizard["data"]["campaign_type"] = ct
        await _show_step(update, context, cur_step+1)
        return
    # geography country picker handlers
    if data.startswith("pick_country:"):
        code = data.split(":")[1]
        picker = context.user_data.get("country_picker", {})
        selected = picker.get("selected", [])
        if code in selected:
            selected.remove(code)
        else:
            selected = [code]
        picker["selected"] = selected
        from app.bot.handlers.pickers import build_country_picker
        lang = context.user_data.get("lang") or "ru"
        text, kb = build_country_picker(query=picker.get("query",""), page=picker.get("page",0), selected=selected, lang=lang)
        await query.edit_message_text(f"{_progress(cur_step)}\n\n<b>{STEP_TITLES[STEPS[cur_step]]}: Страна</b>\n\n" + text, reply_markup=kb, parse_mode="HTML")
        return
    if data.startswith("pick_country_page:"):
        parts = data.split(":")
        page = int(parts[1])
        q = parts[2] if len(parts)>2 else ""
        picker = context.user_data.get("country_picker", {})
        picker["page"] = page
        picker["query"] = q
        from app.bot.handlers.pickers import build_country_picker
        lang = context.user_data.get("lang") or "ru"
        text, kb = build_country_picker(query=q, page=page, selected=picker.get("selected", []), lang=lang)
        await query.edit_message_text(f"{_progress(cur_step)}\n\n<b>{STEP_TITLES[STEPS[cur_step]]}: Страна</b>\n\n" + text, reply_markup=kb, parse_mode="HTML")
        return
    if data == "pick_country_confirm":
        picker = context.user_data.get("country_picker", {})
        selected = picker.get("selected", [])
        if not selected:
            await query.answer("Выберите страну", show_alert=False)
            return
        from app.data.countries import get_country
        c = get_country(selected[0])
        if c:
            wizard["data"]["country"] = c["name_ru"] if c["code"] not in ("ALL","NOT_SPECIFIED") else (c["name_ru"] if c["code"]=="ALL" else "")
        else:
            wizard["data"]["country"] = selected[0]
        context.user_data.pop("country_picker", None)
        # after country, ask city via text
        wizard["audience_substep"] = "city"
        await query.edit_message_text(f"{_progress(cur_step)}\n\nСтрана: <b>{wizard['data']['country'] or 'Все'}</b>\nВведите город или «-» чтобы пропустить:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭ Пропустить", callback_data="wiz_skip_city")]]), parse_mode="HTML")
        return
    if data == "pick_country_cancel":
        wizard["data"]["country"] = ""
        wizard["data"]["city"] = ""
        context.user_data.pop("country_picker", None)
        await _show_step(update, context, cur_step+1)
        return
    if data == "wiz_skip_city":
        wizard["data"]["city"] = ""
        wizard.pop("audience_substep", None)
        await _show_step(update, context, cur_step+1)
        return
    if data.startswith("wiz_audsrc:"):
        src = data.split(":",1)[1]
        wizard["data"]["audience_source"] = src
        await query.edit_message_text(f"{_progress(cur_step)}\n\n<b>Выберите сегмент аудитории:</b>", reply_markup=audience_mode_keyboard(), parse_mode="HTML")
        return
    if data.startswith("wiz_audmode:"):
        mode = data.split(":",1)[1]
        wizard["data"]["audience_mode"] = mode
        wizard["pending_limit"] = True
        await query.edit_message_text(f"{_progress(cur_step)}\n\n<b>Укажите лимит (1–10000):</b>\nЭто цель кампании, не число найденных людей.", reply_markup=back_cancel_keyboard(), parse_mode="HTML")
        return
    if data.startswith("wiz_recip:"):
        val = data.split(":")[1]
        if val == "subscribers":
            wizard["data"]["recipients"] = []
            wizard["data"]["audience_source"] = "bot_subscribers"
            await _show_step(update, context, cur_step+1)
        elif val == "manual":
            wizard["awaiting_recipients"] = True
            await query.edit_message_text(f"{_progress(cur_step)}\n\n<b>Введите получателей через запятую:</b>\nДля Email — адреса, для остальных — ID/username.", reply_markup=back_cancel_keyboard(), parse_mode="HTML")
        elif val == "import":
            wizard["data"]["recipients"] = []
            wizard["data"]["audience_source"] = "imported_list"
            await query.edit_message_text(f"{_progress(cur_step)}\n\nИмпорт: используйте 👥 Аудитории → 📥 Импорт CSV, затем вернитесь. Пока используем подписчиков.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Продолжить", callback_data="wiz_recip:subscribers")]]), parse_mode="HTML")
        return
    if data.startswith("wiz_schedule:"):
        sched = data.split(":",1)[1]
        wizard["data"]["schedule"] = sched
        await _save_wizard(update, context)
        return
    if data == "wiz_confirm":
        await _show_step(update, context, cur_step+1)
        return
    if data == "wiz_edit_text":
        wizard["step"] = STEPS.index("message_text")
        await _show_step(update, context, wizard["step"])
        return
    if data == "wiz_edit_link":
        wizard["step"] = STEPS.index("link")
        await _show_step(update, context, wizard["step"])
        return
    if data.startswith("tpl_use:"):
        tid = data.split(":")[1]
        from app.bot.handlers.templates import TEMPLATES
        tpl = next((t for t in TEMPLATES if t["id"]==tid), None)
        if tpl:
            wizard["data"]["message_text"] = tpl["text"]
            await query.answer("Шаблон применён")
            wizard["step"] = STEPS.index("message_text")
            await _show_step(update, context, wizard["step"])
        return

async def handle_wizard_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wizard = context.user_data.get("wizard")
    if not wizard:
        return
    # country picker search
    if STEPS[wizard["step"]] == "geography" and context.user_data.get("country_picker"):
        from app.bot.handlers.pickers import build_country_picker
        q = update.message.text.strip()
        lang = context.user_data.get("lang") or "ru"
        picker = context.user_data["country_picker"]
        text, kb = build_country_picker(query=q, page=0, selected=picker.get("selected", []), lang=lang)
        picker["query"] = q
        picker["page"] = 0
        await update.message.reply_text(f"{_progress(wizard['step'])}\n\n<b>{STEP_TITLES[STEPS[wizard['step']]]}</b>\n\n" + text, reply_markup=kb, parse_mode="HTML")
        return
    text = update.message.text.strip()
    cur_idx = wizard["step"]
    cur_name = STEPS[cur_idx]
    if wizard.get("pending_limit"):
        try:
            num = int(text)
            if num < 1 or num > 10000:
                await update.message.reply_text("Лимит 1–10000. Попробуйте снова:")
                return
            wizard["data"]["requested_limit"] = num
            wizard.pop("pending_limit", None)
            await update.message.reply_text("Выберите источник аудитории:", reply_markup=audience_source_keyboard())
            return
        except ValueError:
            await update.message.reply_text("Введите число 1–10000, например 100:")
            return
    if wizard.get("awaiting_recipients"):
        parts = [p.strip() for p in text.split(",") if p.strip()]
        if not parts:
            await update.message.reply_text("Укажите хотя бы одного получателя или выберите «Подписчики бота»:")
            return
        wizard["data"]["recipients"] = parts[:100]
        wizard.pop("awaiting_recipients", None)
        await update.message.reply_text(f"Получатели сохранены: {len(parts)}", reply_markup=back_cancel_keyboard())
        await _show_step(update, context, cur_idx+1)
        return
    if wizard.get("audience_substep") == "city":
        if text == "-" or text.lower() == "пропустить":
            wizard["data"]["city"] = ""
        else:
            ok, msg = validate_country_city(wizard["data"]["country"], text)
            if not ok:
                await update.message.reply_text(f"⚠️ {msg}\nПопробуйте снова или «-»:")
                return
            wizard["data"]["city"] = text
        wizard.pop("audience_substep", None)
        await _show_step(update, context, cur_idx+1)
        return
    if cur_name == "message_text":
        if len(text) < 5:
            await update.message.reply_text("Текст слишком короткий (минимум 5 символов). Попробуйте снова:")
            return
        if len(text) > 4096:
            await update.message.reply_text("Текст слишком длинный (макс 4096). Сократите:")
            return
        wizard["data"]["message_text"] = text
        await _show_step(update, context, cur_idx+1)
        return
    if cur_name == "link":
        if text == "-" or text.lower() == "пропустить":
            wizard["data"]["link"] = ""
        else:
            ok, msg = validate_url(text)
            if not ok:
                await update.message.reply_text(f"⚠️ {msg}\nВведите корректный https:// URL или '-' чтобы пропустить:")
                return
            wizard["data"]["link"] = text
        await _show_step(update, context, cur_idx+1)
        return
    await update.message.reply_text("Пожалуйста, следуйте подсказкам мастера или используйте кнопки.")

async def _save_wizard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wizard = context.user_data.get("wizard")
    if not wizard:
        return
    if wizard.get("saved"):
        await update.callback_query.answer("Уже сохраняется...")
        return
    wizard["saved"] = True
    data = wizard["data"]
    user_id = update.effective_user.id
    if data["recipients"] and data["platform"] in ("email", "whatsapp", "facebook_messenger"):
        from app.services.consent_service import ConsentService
        cs = ConsentService(DATABASE_PATH)
        for rec in data["recipients"]:
            await cs.grant(user_id, data["platform"], rec, source="manual_input", display_name=rec)
    import json as _json
    from app.domain.models import Campaign
    campaign = Campaign(
        owner_id=user_id,
        platform=data["platform"],
        campaign_type=data["campaign_type"],
        country=data["country"],
        city=data["city"],
        audience_source=data["audience_source"],
        audience_mode=data["audience_mode"],
        requested_limit=data["requested_limit"],
        message_text=data["message_text"],
        link=data["link"],
        schedule_at=None,
        status="draft",
        recipients_json=_json.dumps(data["recipients"], ensure_ascii=False),
    )
    service = CampaignService(DATABASE_PATH)
    try:
        created = await service.create_draft(campaign)
        if data["recipients"]:
            from app.storage.repositories import ActivityRepo
            ar = ActivityRepo(DATABASE_PATH)
            await ar.log(user_id, created.id, "recipients_set", f"Получателей вручную: {len(data['recipients'])}")
        if data["schedule"] == "now":
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
                    return {"status": "service_error", "hint": str(e)}
            ok, reasons = await service.check_readiness(created.id, user_id, checker)
            from app.services.subscription_service import SubscriptionService
            sub = SubscriptionService(DATABASE_PATH)
            can, msg = await sub.can_send(user_id)
            if not can:
                ok = False
                reasons.append(msg)
            if not ok:
                await update.callback_query.edit_message_text(
                    f"✅ Черновик #{created.id} сохранён, но запуск невозможен:\n\n• " + "\n• ".join(reasons) + "\n\nОткройте карточку кампании.",
                    parse_mode="HTML"
                )
            else:
                await update.callback_query.edit_message_text(
                    f"✅ Кампания #{created.id} готова к запуску!\n\nСтатус: <b>Готова</b>\nОткройте «📋 Мои кампании» → ▶️ Запустить → подтвердить.",
                    parse_mode="HTML"
                )
        else:
            await update.callback_query.edit_message_text(
                f"✅ Черновик #{created.id} сохранён!\n\n"
                f"Канал: {Platform.display(created.platform)}\n"
                f"Статус: Черновик\n\n"
                f"Откройте «📋 Мои кампании» чтобы управлять.",
                parse_mode="HTML"
            )
        context.user_data.pop("wizard", None)
        context.user_data.pop("country_picker", None)
    except Exception as e:
        logger.exception(f"save wizard error: {e}")
        await update.callback_query.edit_message_text(f"❌ Ошибка сохранения: {e}")
        wizard["saved"] = False
