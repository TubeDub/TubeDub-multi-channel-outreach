import asyncio
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from app.config import DATABASE_PATH, TELEGRAM_BOT_TOKEN, LOG_LEVEL
from app.observability.logging_config import setup_logging, get_logger
from app.storage.database import init_db

setup_logging(LOG_LEVEL)
logger = get_logger(__name__)

async def post_init(app):
    await init_db(DATABASE_PATH)
    logger.info(f"Database initialized at {DATABASE_PATH} (token hidden)")
    # Восстановление очереди после рестарта — не теряем задания
    try:
        from app.storage.repositories import CampaignRepo, DeliveryRepo
        repo = CampaignRepo(DATABASE_PATH)
        # проверяем что БД создана
        import aiosqlite
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute("SELECT id, owner_id, platform, status, requested_limit FROM campaigns WHERE status IN ('queued','running','paused')")
            rows = await cur.fetchall()
            if rows:
                logger.info(f"Восстановление очереди: найдено {len(rows)} незавершённых кампаний")
                for r in rows:
                    logger.info(f"  кампания #{r[0]} owner={r[1]} platform={r[2]} status={r[3]} цель={r[4]} — остаётся в статусе {r[3]}, ожидаёт ручного продолжения или автоматического рестарта")
                # не стартуем автоматически без подтверждения пользователя, но сохраняем состояние
                # delivery статусы pending/ retry остаются в БД и будут продолжены при следующем run_campaign
    except Exception as e:
        logger.warning(f"Очередь восстановление: {e}")

def build_app():
    from app.bot.handlers.start import start_handler, menu_handler, help_handler, cancel_handler, stop_handler, unknown_text_handler, language_handler, handle_language_callback
    from app.bot.handlers.wizard import handle_wizard_callback, start_wizard
    from app.bot.handlers.campaigns import handle_campaign_callback
    from app.bot.handlers.history import show_history, show_reports
    from app.bot.handlers.integrations import show_connections, handle_integrations_callback, handle_channel_input
    from app.bot.handlers.settings import show_settings, handle_settings_callback, handle_settings_input
    from app.bot.handlers.account import show_account
    from app.bot.handlers.subscription import handle_subscription_callback, handle_admin_payments
    from app.bot.handlers.stats import show_stats
    from app.bot.handlers.diagnostics import show_diagnostics, handle_diagnostics_callback
    from app.bot.handlers.accounts import show_accounts, handle_accounts_callback, handle_accounts_input
    from app.bot.handlers.audiences import show_audiences, handle_audiences_callback, handle_audiences_input
    from app.bot.handlers.templates import show_templates, handle_templates_callback

    token = TELEGRAM_BOT_TOKEN or os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не настроен. Добавьте его в .env (см. .env.example)")

    app = ApplicationBuilder().token(token).post_init(post_init).build()

    # commands — расширенные для диагностики и языка
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("menu", menu_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("cancel", cancel_handler))
    app.add_handler(CommandHandler("stop", stop_handler))
    app.add_handler(CommandHandler("account", show_account))
    app.add_handler(CommandHandler("stats", show_stats))
    app.add_handler(CommandHandler("accounts", show_accounts))
    app.add_handler(CommandHandler("audiences", show_audiences))
    app.add_handler(CommandHandler("templates", show_templates))
    app.add_handler(CommandHandler("diagnostics", show_diagnostics))
    app.add_handler(CommandHandler("diagnostic", show_diagnostics))
    app.add_handler(CommandHandler("check", show_diagnostics))
    app.add_handler(CommandHandler("language", language_handler))
    app.add_handler(CommandHandler("lang", language_handler))

    # Callback handlers — specific first (порядок важен для pick_*)
    app.add_handler(CallbackQueryHandler(handle_wizard_callback, pattern=r"^(wiz_.*|pick_country.*|wiz_skip_city)"))
    app.add_handler(CallbackQueryHandler(handle_campaign_callback, pattern=r"^camp_.*"))
    app.add_handler(CallbackQueryHandler(handle_accounts_callback, pattern=r"^(go_accounts|acc_.*)"))
    app.add_handler(CallbackQueryHandler(handle_audiences_callback, pattern=r"^(go_audiences|aud_.*)"))
    app.add_handler(CallbackQueryHandler(handle_templates_callback, pattern=r"^(go_templates|tpl_.*)"))
    app.add_handler(CallbackQueryHandler(handle_integrations_callback, pattern=r"^conn_.*"))
    app.add_handler(CallbackQueryHandler(handle_settings_callback, pattern=r"^(settings_.*|pick_country.*|pick_lang.*|set_lang.*|go_settings)"))
    app.add_handler(CallbackQueryHandler(handle_subscription_callback, pattern=r"^(go_subscription|sub_.*|admin_.*)"))
    app.add_handler(CallbackQueryHandler(show_diagnostics, pattern=r"^go_diagnostics$"))
    app.add_handler(CallbackQueryHandler(handle_language_callback, pattern=r"^set_lang:.*"))
    app.add_handler(CallbackQueryHandler(lambda u,c: show_account(u,c), pattern=r"^go_account$"))
    app.add_handler(CallbackQueryHandler(lambda u,c: show_stats(u,c), pattern=r"^go_stats$"))
    app.add_handler(CallbackQueryHandler(lambda u,c: show_connections(u,c), pattern=r"^go_connections$"))
    app.add_handler(CallbackQueryHandler(lambda u,c: show_settings(u,c), pattern=r"^go_settings$"))
    app.add_handler(CallbackQueryHandler(show_history, pattern=r"^go_history$"))
    app.add_handler(CallbackQueryHandler(show_reports, pattern=r"^go_reports$"))
    app.add_handler(CallbackQueryHandler(show_stats, pattern=r"^go_campaigns$"))
    app.add_handler(CallbackQueryHandler(lambda u,c: u.callback_query.answer(), pattern=r"^noop$"))

    async def unified_text(update, context):
        if await handle_accounts_input(update, context):
            return
        if await handle_audiences_input(update, context):
            return
        if await handle_channel_input(update, context):
            return
        if await handle_settings_input(update, context):
            return
        from app.bot.handlers.campaigns import handle_edit_text
        if context.user_data.get("edit_state"):
            await handle_edit_text(update, context)
            return
        # picker search already handled in start unknown handler? but handle here too
        if context.user_data.get("country_picker") or context.user_data.get("language_picker"):
            # settings picker search
            if await handle_settings_input(update, context):
                return
            # wizard picker search
            from app.bot.handlers.wizard import handle_wizard_text
            if context.user_data.get("wizard"):
                await handle_wizard_text(update, context)
                return
        if context.user_data.get("wizard"):
            from app.bot.handlers.wizard import handle_wizard_text
            await handle_wizard_text(update, context)
            return
        await unknown_text_handler(update, context)

    app.add_handler(MessageHandler(filters.Document.ALL, unified_text))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unified_text))

    async def generic_menu_callback(update, context):
        q = update.callback_query
        await q.answer()
        data = q.data
        if data == "go_menu":
            from app.bot.keyboards import main_menu_keyboard
            lang = context.user_data.get("lang") or "ru"
            await q.message.reply_text("🏠 Главное меню — выберите действие:", reply_markup=main_menu_keyboard(lang))
        elif data == "go_history":
            await show_history(update, context)
        elif data == "go_reports":
            await show_reports(update, context)
        elif data == "go_connections":
            await show_connections(update, context)
        elif data == "go_diagnostics":
            await show_diagnostics(update, context)
        elif data == "go_accounts":
            await show_accounts(update, context)
        elif data == "go_audiences":
            await show_audiences(update, context)
        elif data == "go_templates":
            await show_templates(update, context)
        elif data == "go_settings":
            await show_settings(update, context)
        elif data == "go_help":
            await help_handler(update, context)
        elif data == "go_language":
            await language_handler(update, context)
        elif data == "admin_payments":
            await handle_admin_payments(update, context)

    app.add_handler(CallbackQueryHandler(generic_menu_callback, pattern=r"^go_.*"))

    return app

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не настроен. Создайте .env из .env.example и укажите токен.")
        print("DATABASE_PATH =", DATABASE_PATH)
        return
    app = build_app()
    logger.info("Bot starting polling (token hidden)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
