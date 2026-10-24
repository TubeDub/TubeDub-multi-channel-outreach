# Аудитории — импорт, дедупликация, фильтры

## Источники
- `bot_subscribers` — пользователи, написавшие боту + прошедшие `/start`
- `imported_list` — CSV импорт
- Личный Telegram — диалоги `get_available_dialogs` (только ваши контакты, не спам)

## Формат CSV
```csv
external_id,provider,display_name
+380501234567,whatsapp,Иван
user@example.com,email,Мария
123456789,telegram,Пётр
```

## Правила
- Дедупликация по `(owner_id, provider, external_id)` — UNIQUE в БД + `seen` в импорте
- Валидация: email содержит `@`, whatsapp — телефон, telegram — chat_id/username
- Согласие: при импорте `consent_status=granted`, `consent_source=csv_import:filename`, `consent_at=now`
- Исключение: при отправке `ConsentService.is_consented` → если `unsubscribed_at` или `consent_status != granted` → `skipped` (не `sent`)

## Интерфейс
- `👥 Аудитории` → `📥 Импорт CSV` (документ или текст), `🔍 Фильтр`, `🗑 Дедупликация`, `📤 Экспорт`
- Фильтр: по `provider`, `country`/`language` (если хранятся в `display_name`/meta), поиск по `external_id`
- Честная проверка `check_sendable` перед `prepare_queue` — не обещаем отправить тому, кому нельзя
