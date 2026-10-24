from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

# ─── Главное меню — профессиональный SaaS ───
def main_menu_keyboard(lang: str = "ru"):
    from app.i18n.translator import t
    # локализованные названия, но кнопки должны матчиться на любом языке — оставляем иконки
    kb = [
        [t("btn_create", lang), t("btn_campaigns", lang)],
        ["👥 Аудитории", "👥 Мои аккаунты"],
        ["🕘 История", "📊 Отчёты"],
        [t("btn_stats", lang), t("btn_connections", lang)],
        [t("btn_account", lang), t("btn_subscription", lang)],
        [t("btn_settings", lang), t("btn_help", lang)],
        ["🌐 Язык", "🔍 Диагностика"],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True, is_persistent=True)

def language_keyboard():
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="set_lang:ru")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="set_lang:en")],
        [InlineKeyboardButton("🇺🇦 Українська", callback_data="set_lang:uk")],
    ])

# ─── Платформы ───
def platform_keyboard(connections: dict):
    platforms = [
        ("telegram_user", "Telegram Личный"),
        ("telegram", "Telegram Бот"),
        ("facebook_messenger", "Facebook Messenger"),
        ("instagram", "Instagram"),
        ("whatsapp", "WhatsApp"),
        ("tiktok", "TikTok"),
        ("email", "Email"),
    ]
    status_emoji = {
        "connected": "✅ Подключён",
        "not_connected": "⚪ Не подключён",
        "configuration_error": "🟡 Ошибка конфигурации",
        "permission_error": "🟠 Нет разрешений",
        "service_error": "🔴 Сервис недоступен",
        "needs_permissions": "🟠 Нет разрешений",
        "unavailable": "🔴 Недоступен",
    }
    rows = []
    for val, label in platforms:
        st = connections.get(val, "not_connected")
        hint = status_emoji.get(st, st)
        rows.append([InlineKeyboardButton(f"{label} — {hint}", callback_data=f"wiz_platform:{val}")])
    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="wiz_back"), InlineKeyboardButton("❌ Отмена", callback_data="wiz_cancel")])
    return InlineKeyboardMarkup(rows)

def campaign_type_keyboard(platform: str):
    options = [
        ("own_channel_post", "📢 Публикация в канал"),
        ("audience_message", "💬 Личное сообщение"),
        ("ads_campaign", "📈 Реклама (Ads)"),
    ]
    rows = [[InlineKeyboardButton(label, callback_data=f"wiz_ctype:{val}")] for val, label in options]
    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="wiz_back"), InlineKeyboardButton("❌ Отмена", callback_data="wiz_cancel")])
    return InlineKeyboardMarkup(rows)

def audience_source_keyboard():
    options = [
        ("own_channel", "📢 Собственный канал"),
        ("bot_subscribers", "🤖 Подписчики бота"),
        ("imported_list", "📥 Импорт списка"),
        ("inbound_leads", "📩 Входящие лиды"),
        ("ads_audience", "🎯 Рекламная аудитория"),
    ]
    rows = [[InlineKeyboardButton(label, callback_data=f"wiz_audsrc:{val}")] for val, label in options]
    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="wiz_back"), InlineKeyboardButton("❌ Отмена", callback_data="wiz_cancel")])
    return InlineKeyboardMarkup(rows)

def audience_mode_keyboard():
    rows = [
        [InlineKeyboardButton("👥 Подписчики", callback_data="wiz_audmode:subscribers")],
        [InlineKeyboardButton("🎯 Потенц. клиенты", callback_data="wiz_audmode:leads")],
        [InlineKeyboardButton("👥+🎯 Обе группы", callback_data="wiz_audmode:both")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="wiz_back"), InlineKeyboardButton("❌ Отмена", callback_data="wiz_cancel")],
    ]
    return InlineKeyboardMarkup(rows)

# Шаг 3 — получатели
def recipients_keyboard():
    rows = [
        [InlineKeyboardButton("📝 Ввести вручную", callback_data="wiz_recip:manual")],
        [InlineKeyboardButton("👥 Использовать подписчиков бота", callback_data="wiz_recip:subscribers")],
        [InlineKeyboardButton("📥 Выбрать из импорта (позже)", callback_data="wiz_recip:import")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="wiz_back"), InlineKeyboardButton("❌ Отмена", callback_data="wiz_cancel")],
    ]
    return InlineKeyboardMarkup(rows)

def schedule_keyboard():
    rows = [
        [InlineKeyboardButton("💾 Сохранить черновик", callback_data="wiz_schedule:draft")],
        [InlineKeyboardButton("🚀 Запустить сейчас", callback_data="wiz_schedule:now")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="wiz_back"), InlineKeyboardButton("❌ Отмена", callback_data="wiz_cancel")],
    ]
    return InlineKeyboardMarkup(rows)

def back_cancel_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="wiz_back"), InlineKeyboardButton("❌ Отмена", callback_data="wiz_cancel")]])

def preview_keyboard():
    rows = [
        [InlineKeyboardButton("✅ Подтвердить и сохранить", callback_data="wiz_confirm")],
        [InlineKeyboardButton("✏️ Изменить текст", callback_data="wiz_edit_text"), InlineKeyboardButton("🔗 Изменить ссылку", callback_data="wiz_edit_link")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="wiz_back"), InlineKeyboardButton("❌ Отмена", callback_data="wiz_cancel")],
    ]
    return InlineKeyboardMarkup(rows)

# ─── Кампании ───
def campaign_list_keyboard(campaigns, page, total_pages):
    rows = []
    for c in campaigns:
        from app.domain.statuses import CampaignStatus, Platform
        label = f"#{c.id} · {Platform.display(c.platform)} · {c.country or '—'} · {CampaignStatus.display(c.status)}"
        rows.append([InlineKeyboardButton(label, callback_data=f"camp_open:{c.id}")])
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀️ Назад", callback_data=f"camp_list:{page-1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("Вперёд ▶️", callback_data=f"camp_list:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("🏠 Меню", callback_data="go_menu")])
    return InlineKeyboardMarkup(rows)

def campaign_card_keyboard(campaign):
    rows = []
    rows.append([InlineKeyboardButton("👁 Детали", callback_data=f"camp_view:{campaign.id}")])
    rows.append([InlineKeyboardButton("✏️ Редактировать", callback_data=f"camp_edit:{campaign.id}"), InlineKeyboardButton("📄 Дублировать", callback_data=f"camp_dup:{campaign.id}")])
    if campaign.status in ("draft", "needs_setup", "ready", "failed", "cancelled"):
        rows.append([InlineKeyboardButton("▶️ Запустить", callback_data=f"camp_run:{campaign.id}")])
    if campaign.status in ("queued", "running"):
        rows.append([InlineKeyboardButton("⏸ Пауза", callback_data=f"camp_pause:{campaign.id}"), InlineKeyboardButton("🛑 Отменить", callback_data=f"camp_cancel:{campaign.id}")])
    if campaign.status == "paused":
        rows.append([InlineKeyboardButton("▶️ Продолжить", callback_data=f"camp_resume:{campaign.id}"), InlineKeyboardButton("🛑 Отменить", callback_data=f"camp_cancel:{campaign.id}")])
    rows.append([InlineKeyboardButton("🗑 Удалить", callback_data=f"camp_del:{campaign.id}")])
    rows.append([InlineKeyboardButton("⬅️ К списку", callback_data="camp_list:1"), InlineKeyboardButton("🏠 Меню", callback_data="go_menu")])
    return InlineKeyboardMarkup(rows)

def confirm_delete_keyboard(campaign_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Да, удалить", callback_data=f"camp_del_confirm:{campaign_id}")],
        [InlineKeyboardButton("❌ Отмена", callback_data=f"camp_open:{campaign_id}")],
    ])

def confirm_run_keyboard(campaign_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить запуск", callback_data=f"camp_run_confirm:{campaign_id}")],
        [InlineKeyboardButton("❌ Отмена", callback_data=f"camp_open:{campaign_id}")],
    ])

# ─── Подключения ───
def connections_keyboard(providers_status: dict):
    rows = []
    for plat, info in providers_status.items():
        st = info.get("status", "not_connected")
        emoji = {"connected":"✅","not_connected":"⚪","configuration_error":"🟡","permission_error":"🟠","service_error":"🔴","needs_permissions":"🟠","unavailable":"🔴"}.get(st,"•")
        label = plat.replace("_"," ").title()
        rows.append([InlineKeyboardButton(f"{emoji} {label} — {st}", callback_data=f"conn_check:{plat}")])
    rows.append([InlineKeyboardButton("🔄 Проверить Telegram", callback_data="conn_check:telegram")])
    rows.append([InlineKeyboardButton("🏠 Меню", callback_data="go_menu")])
    return InlineKeyboardMarkup(rows)

def connection_detail_keyboard(platform: str, status: str):
    rows = []
    if platform == "telegram" and status == "connected":
        rows.append([InlineKeyboardButton("✉️ Тест себе", callback_data=f"conn_sendtest:{platform}")])
        rows.append([InlineKeyboardButton("⚙️ Настроить канал", callback_data="conn_set_channel")])
    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="go_connections")])
    rows.append([InlineKeyboardButton("🏠 Меню", callback_data="go_menu")])
    return InlineKeyboardMarkup(rows)

# ─── Настройки ───
def settings_keyboard(lang: str = "ru"):
    rows = [
        [InlineKeyboardButton("🌍 Страна", callback_data="set_country")],
        [InlineKeyboardButton("🌐 Язык", callback_data="set_lang_picker")],
        [InlineKeyboardButton("🕐 Часовой пояс", callback_data="set_tz")],
        [InlineKeyboardButton("🧪 Тест-режим", callback_data="set_testmode")],
        [InlineKeyboardButton("🔔 Уведомления", callback_data="set_notif")],
        [InlineKeyboardButton("🏠 Меню", callback_data="go_menu")],
    ]
    return InlineKeyboardMarkup(rows)

def edit_choice_keyboard(campaign_id):
    rows = [
        [InlineKeyboardButton("📝 Текст", callback_data=f"camp_edit_field:{campaign_id}:text")],
        [InlineKeyboardButton("🔗 Ссылка", callback_data=f"camp_edit_field:{campaign_id}:link")],
        [InlineKeyboardButton("🌍 География", callback_data=f"camp_edit_field:{campaign_id}:geo")],
        [InlineKeyboardButton("📊 Лимит", callback_data=f"camp_edit_field:{campaign_id}:limit")],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"camp_open:{campaign_id}")],
    ]
    return InlineKeyboardMarkup(rows)

# ─── Подписка ───
def subscription_main_keyboard(has_active: bool, has_pending: bool):
    rows = []
    if has_active:
        rows.append([InlineKeyboardButton("✅ Подписка активна", callback_data="sub_status")])
    else:
        rows.append([InlineKeyboardButton("💳 Оформить за $1/мес", callback_data="sub_buy")])
        if not has_pending:
            rows.append([InlineKeyboardButton("📋 Условия", callback_data="sub_terms")])
        else:
            rows.append([InlineKeyboardButton("⏳ Заявка на рассмотрении", callback_data="sub_status")])
    rows.append([InlineKeyboardButton("📜 Мои заявки", callback_data="sub_history")])
    rows.append([InlineKeyboardButton("❓ Помощь", callback_data="sub_help"), InlineKeyboardButton("🏠 Меню", callback_data="go_menu")])
    return InlineKeyboardMarkup(rows)

def subscription_offer_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Оформить подписку", callback_data="sub_buy")],
        [InlineKeyboardButton("📋 Условия подписки", callback_data="sub_terms")],
        [InlineKeyboardButton("❓ Помощь", callback_data="go_help")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="go_menu")],
    ])

def payment_confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Я оплатил", callback_data="sub_paid")],
        [InlineKeyboardButton("❌ Отмена", callback_data="go_subscription")],
    ])

def admin_payment_keyboard(request_id: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить", callback_data=f"admin_approve:{request_id}"), InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject:{request_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin_payments")],
    ])

# ─── Аккаунт ───
def account_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Подписка", callback_data="go_subscription")],
        [InlineKeyboardButton("📊 Статистика", callback_data="go_stats")],
        [InlineKeyboardButton("🏠 Меню", callback_data="go_menu")],
    ])

# ─── Статистика ───
def stats_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Мои кампании", callback_data="go_campaigns")],
        [InlineKeyboardButton("🔌 Подключения", callback_data="go_connections")],
        [InlineKeyboardButton("🏠 Меню", callback_data="go_menu")],
    ])
