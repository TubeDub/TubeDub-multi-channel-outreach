# Telegram Личный аккаунт — реальная интеграция (Telethon)

## Принцип
- Отдельно от Telegram Bot API. Бот — только интерфейс управления (команды, кнопки, уведомления).
- Отправитель для outreach — **ваш личный аккаунт** через Telethon (MTProto), сессия per `owner_id`.
- Без `TELEGRAM_API_ID/HASH` — статус `not_connected` + `configuration_error` с инструкцией, не падаем.

## Получение API ключей
1. Перейдите https://my.telegram.org → API development tools
2. Создайте app (App title, Short name — любые)
3. Скопируйте `API ID` (число) и `API HASH` (строка)
4. Добавьте в `.env`:
```
TELEGRAM_API_ID=1234567
TELEGRAM_API_HASH=abc123...
```

## Подключение в боте
- `👥 Мои аккаунты` → `👤 Telegram Личный` → `🔗 Подключить`
- Введите номер в формате `+380...` → бот вызывает `TelegramClient.send_code_request` (Telethon)
- Введите код из Telegram (придёт в личные сообщения/СМС) → если включен 2FA, введите пароль
- При успехе создаётся `data/sessions/{owner_id}.session` — не коммитится, восстанавливается после рестарта
- `check_connection`: если `.session` есть + `client.get_me()` успешен → `connected`, иначе `not_connected/configuration_error`

## Ограничения честности
- Отправка только тем, кому разрешено правилами Telegram (ваши контакты, диалоги где вы участник, каналы где вы админ — не спам рандомным пользователям)
- FloodWait → `RateLimitError` с честной статистикой (retry_delay), не обходим лимиты
- Заблокировавшие вас → `ForbiddenError` → `blocked`/`skipped` без фейк-`sent`
- Отключённые/пустые username → проверка `resolve_sender` + `is_externally_managed` → реальные адресаты
- Статистика: `sent` только после реального `client.send_message`/`send_file`, иначе `failed/rate_delay/skipped`

## Хранение и безопасность
- Сессии изолированы: `owner_id` → отдельный файл, не пересекаются между пользователями
- `TELEGRAM_API_ID/HASH` — в `.env` (не показывать в логах, `mask_token`), `PHONE`/`CODE`/`2FA` — только в памяти на время auth, не логировать
- Отключение: `Мои аккаунты` → `❌ Отключить` → удаляет `.session` + запись `provider_connections`

## Проверка
```bash
PYTHONPATH=. pytest -q
```
- Без ключей тест `TelegramUserProvider` вернёт `not_connected` (не падает)
- С ключами и сессией — `connected` и реальные `send_message` (требует ручного теста с реальным аккаунтом)
