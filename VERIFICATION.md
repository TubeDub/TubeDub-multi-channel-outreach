# Верификация реальной работы (§18 ТЗ)

Дата: 2026-10-24, окружение Lviv/UA

## Критерии готовности
1. **Реальный отправитель** — `telegram_user` через Telethon MTProto, сессия `data/sessions/{owner_id}.session`, `check_connection` через `client.get_me()`, `send_message` через `client.send_message(entity, message)` — только после auth (API_ID/HASH/phone+code+2FA). Бот `TelegramProvider` — отдельный отправитель через Bot API `sendMessage/publish`, не подменяет личный.
2. **Реальные адресаты** — `ContactRepo` + `ConsentService` → `consent_status=granted` и отсутствие `unsubscribed_at`. Источники: `bot_subscribers` (регистрация через /start), `imported_list` (CSV импорт), диалоги личного аккаунта `get_available_dialogs` (только ваши контакты). Нет фейк-адресатов админа.
3. **Реальные API-запросы** — `httpx.AsyncClient` для Bot API, `telethon.TelegramClient` для личного, `META Graph API` заготовки (не заглушка `ok=True`). `delivery_service` вызывает `provider.send_message` и `publish`, различает `RateLimitError/FloodWait`, `ForbiddenError/blocked`, `NotFoundError`, `ProviderError` — все отражаются в `deliveries.status`, без `sent` при ошибке.
4. **Честная статистика** — 8 статусов: `pending/sent/delivered/failed/blocked/skipped/rate_delay/cancelled` + счётчики `requested/available/sent/failed/skipped/rate_delay`. Успех только после `response.ok`, `completed` только когда все `deliveries` в финальном состоянии, пауза/продолжение/отмена/рестарт без дублей (idempotency_key).

## Как проверить вручную
```bash
cp .env.example .env  # заполните TELEGRAM_BOT_TOKEN, TELEGRAM_API_ID/HASH
python -m pytest -q  # 89 passed (включая test_iteration3)
python app/storage/migrations/migrate.py
python -m app
```
- В Telegram: `/start` → язык → страна (поиск) → `👥 Мои аккаунты` → `Telegram Личный` → Подключить → +380… → код → 2FA → `✅ connected` + сессия `data/sessions/{your_id}.session`
- `🔍 Диагностика` — все 6 каналов с last_check и next_step
- `👥 Аудитории` → `📥 Импорт CSV` → загрузите `external_id,provider` → `✅ Импортировано 2, дублей 1`
- `🎯 Создать` → 9 шагов (канал→тип→аудитория→гео→получатели→текст→ссылка→предпросмотр→запуск) → предпросмотр показывает реальные данные → `Сохранить черновик` или `Запустить сейчас` (проверка подписки 10 free → $1 manual)
- `📋 Мои кампании` → `▶️ Запустить` → очередь создаёт отдельные `deliveries`, лимиты `telegram_user 0.7s` соблюдаются (не обходим), `⏸ Пауза` / `▶️ Продолжить` / `🛑 Отмена` / `🔄 Рестарт` — восстановление после рестарта без дублей
- `📊 Отчёты` → честные цифры: `выбрано/доступно/ожидает/отправляется/принято/доставлено/ошибка/пропущено`

## Автоматические проверки
- `test_telegram_user_provider_honest_statuses` — без ключей `not_connected`, send → ProviderError с кодом
- `test_audience_import_dedup` — CSV дубликаты/невалид отфильтрованы, уникальность БД
- `test_wizard_has_nine_steps` — 9 шагов, titles, progress
- `test_provider_isolation` — Messenger `not_connected` не ломает Telegram
- `test_critical_goal` — цель 100 успешных, FloodWait retry, восстановление после рестарта, blocked→skipped
- `test_mandatory_20` + `test_final_requirements` — honest stats, subscription, startup isolation

## Безопасность (§16)
- Токены/сессии не в логах, `mask_token`/`mask_card_number`, `.env` не коммитится, `data/sessions/` в `.gitignore`
- Per-owner изоляция: `owner_id` в `ProviderConnection`, `Contact`, `Campaign`, `Delivery` — каждый видит только своё
- Manual placeholder оплата $1/30дн — без хранения карт, только `payment_pending` → админ подтверждает

Протоколы: логи `app/observability/logging_config.py` с level INFO, без секретов; миграции с backup; WAL.
