from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from app.config import DATABASE_PATH
from app.services.audience_import_service import AudienceImportService

async def show_audiences(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id=update.effective_user.id if update.effective_user else 0
    svc=AudienceImportService(DATABASE_PATH)
    contacts=await svc.list_contacts(user_id, limit=20)
    text="👥 <b>Аудитории и контакты</b>\n━━━━━━━━━━━━━━━\n"
    if not contacts:
        text+="Пока нет контактов. Добавьте через импорт CSV или они появятся после регистрации пользователей.\n\n"
    else:
        text+=f"Всего контактов: {len(contacts)} (показано 20)\n"
        for c in contacts[:10]:
            text+=f"• {c.provider} — {c.external_id} — {c.display_name or '—'} — {c.consent_status}\n"
        text+="\n"
    text+= (
        "Для каждого канала — свои идентификаторы (Telegram chat_id/username, Email, WhatsApp +тел, Messenger PSID)\n"
        "Контакт доступен только если есть согласие. Отписавшиеся исключаются автоматически.\n"
        "\n<b>Источники:</b> контакты пользователя, доступные диалоги личного аккаунта, импортированные CSV\n"
        "Не обещаем писать любому пользователю Telegram — только разрешённым адресатам.\n"
    )
    kb=InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 Импорт CSV", callback_data="aud_import")],
        [InlineKeyboardButton("🔍 Фильтр", callback_data="aud_filter")],
        [InlineKeyboardButton("🗑 Удалить дубликаты", callback_data="aud_dedup")],
        [InlineKeyboardButton("📤 Экспорт", callback_data="aud_export")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="go_menu")]
    ])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

async def handle_audiences_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query
    await query.answer()
    data=query.data
    if data=="aud_import":
        context.user_data["awaiting_csv"]=True
        await query.edit_message_text(
            "📥 <b>Импорт контактов</b>\n\nОтправьте CSV файл с колонками:\n<code>external_id,provider,display_name</code>\nПример:\n<code>+380501234567,whatsapp,Иван\nuser@example.com,email,Мария\n123456789,telegram,Пётр</code>\n\nДубликаты удаляются, некорректные пропускаются. Согласие считается подтверждённым импортом.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="go_audiences")]]), parse_mode="HTML"
        )
    elif data=="aud_filter":
        await query.edit_message_text("🔍 Фильтр по стране/языку — используйте мастер кампании (шаг Аудитория) или напишите поиск в этом чате.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="go_audiences")]]))
    elif data=="aud_dedup":
        user_id=update.effective_user.id
        svc=AudienceImportService(DATABASE_PATH)
        removed=await svc.remove_duplicates(user_id)
        await query.edit_message_text(f"✅ Дубликаты проверены. Уникальность уже обеспечена БД (owner_id+provider+external_id).", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="go_audiences")]]))
    elif data=="aud_export":
        user_id=update.effective_user.id
        svc=AudienceImportService(DATABASE_PATH)
        contacts=await svc.list_contacts(user_id, limit=1000)
        if not contacts:
            await query.edit_message_text("Нет контактов для экспорта.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="go_audiences")]]))
            return
        import csv, io
        out=io.StringIO()
        writer=csv.DictWriter(out, fieldnames=["external_id","provider","display_name","consent_status","consent_source"])
        writer.writeheader()
        for c in contacts:
            writer.writerow({"external_id":c.external_id,"provider":c.provider,"display_name":c.display_name,"consent_status":c.consent_status,"consent_source":c.consent_source})
        data=out.getvalue()
        await query.edit_message_text(f"📤 Экспорт {len(contacts)} контактов готов. Скопируйте CSV:\n\n<pre>{data[:3000]}</pre>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="go_audiences")]]), parse_mode="HTML")
    elif data=="go_audiences":
        await show_audiences(update, context)

async def handle_audiences_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_csv"):
        user_id=update.effective_user.id
        svc=AudienceImportService(DATABASE_PATH)
        # поддержка документов и текста
        if update.message.document:
            file=await update.message.document.get_file()
            file_bytes=await file.download_as_bytearray()
            imported, dups, errors=await svc.import_csv(user_id, bytes(file_bytes), filename=update.message.document.file_name)
        else:
            # текст как CSV
            txt=update.message.text
            imported, dups, errors=await svc.import_csv(user_id, txt.encode(), filename="text.csv")
        context.user_data.pop("awaiting_csv",None)
        text=f"✅ Импорт завершён:\nИмпортировано: {imported}\nДубликатов пропущено: {dups}\n"
        if errors:
            text+="Ошибки:\n"+"\n".join(errors[:5])
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👥 К аудиториям", callback_data="go_audiences")]]))
        return True
    return False
