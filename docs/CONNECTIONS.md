# Центр подключений — 6 карточек

Каждая карточка показывает:
- **Статус**: `connected` ✅ / `not_connected` ⚪ / `configuration_error` 🟡 / `permission_error` 🟠 / `service_error` 🔴
- **Аккаунт**: username/email/phone или session (для Telegram личного)
- **Возможности**: `send_message`, `publish_to_channel`, `check_connection`
- **last_check_error_reason**: последний текст ошибки (visible)
- **next_step**: что делать (ссылка на кабинет/документацию)

## Карточки
1. **Telegram Бот** — `TELEGRAM_BOT_TOKEN`, проверяется через `getMe`, mask token
2. **Telegram Личный** — `TELEGRAM_API_ID/HASH` + сессия, см. docs/TELEGRAM_PERSONAL.md
3. **Facebook Messenger** — `META_ACCESS_TOKEN` + Page, требует `pages_messaging`
4. **Instagram** — `META_ACCESS_TOKEN` + Professional Account, `instagram_manage_messages`
5. **WhatsApp** — `WHATSAPP_TOKEN` + `PHONE_NUMBER_ID`
6. **Email** — `SMTP_HOST/USER/PASSWORD`

Изоляция: ошибка одного провайдера не ломает другие (try/except per check). См. `app/providers/*` и `app/bot/handlers/accounts.py`.

