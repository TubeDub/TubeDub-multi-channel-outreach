# Multi-Channel Personal Outreach — личные аккаунты (Telethon/instagrapi/fbchat/WhatsApp)

Система массовых рассылок **с личных аккаунтов** через Telegram-бота как интерфейс управления. Личные аккаунты = прогрессивный лимитер + антибан. Не использует Bot API для рассылки.

## Быстрый старт (Codespaces)

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://github.com/codespaces/new)

```bash
cp .env.example .env  # заполните TELEGRAM_BOT_TOKEN + TELEGRAM_API_ID/HASH
pip install -r requirements.txt  # telethon + cryptg + instagrapi + fbchat + pyaileys
pytest -q  # 89 passed
python app/storage/migrations/migrate.py
python main.py  # или python -m app
# Откройте бота → /start → Мои аккаунты → подключите личный Telegram/Instagram/...
```

## Получить API ID/HASH (Telegram)

https://my.telegram.org → API development tools → Create app → скопировать `API ID/HASH` → `.env`:
```
TELEGRAM_API_ID=1234567
TELEGRAM_API_HASH=abcdef...
SESSIONS_DIR=./data/sessions
TELEGRAM_BOT_TOKEN=  # от @BotFather, только для управления
```

## Подключение личных аккаунтов

- **Telegram:** `Мои аккаунты → Telegram` → `+380...` → код → 2FA → сессия `data/sessions/user_{id}.session` (не в git), проверка `get_me()`
- **Instagram:** `instagrapi` → логин/пароль → сессия `instagram_{id}.json` → проверка `account_info`, отправка `direct_send`
- **Messenger:** `fbchat` → email/пароль → сессия `fb_{id}.json` → отправка `ThreadType.USER`
- **WhatsApp:** QR-сессия `wa_{id}.json` → отправка по телефону, проверка номера

Каждый канал — отдельный провайдер `app/providers/*_personal_provider.py` с `check_connection/send_message`, учитывает лимитер.

**Важно:** Если выбран `Мой Telegram-аккаунт` → `TelegramUserProvider` (Telethon), не Bot API. При невалидной сессии — не запускается, не переключается молча.

## Мастер кампании (8 шагов, не сбрасывается после числа)

1. Канал (Telegram/Instagram/Messenger/WhatsApp)
2. Тип аудитории
3. Страна (picker с поиском)
4. Город (ввод/пропуск)
5. Источник получателей: вручную `username,phone` через запятую **или** указать количество (лимит)
6. Текст с `{name}` + вариации (5 шаблонов, spintax)
7. Ссылка (опционально)
8. Предпросмотр → Подтверждение → Запуск/Черновик

Мастер хранит `wizard.data` и не сбрасывается после ввода числа — все шаги последовательно.

## Прогрессивный лимитер (обязательно)

Автостадии по `first_seen_at`: NEW 0-7д → 8/5/8/5, WARMING 8-30 → 20/15/20/15, ESTABLISHED 31-90 → 40/30/35/30, MATURE 90+ → 60/50/50/50 (telegram/insta/messenger/wa). Почасовые 2/3 vs 5/8, задержки 45-180с telegram (60-240 insta etc.), FloodWait/PeerFlood → пауза + 2ч cooldown при 3 ошибках. Сообщение пользователю: «Аккаунт прогревается. Сегодня можно ещё X» / «Аккаунт готов. Осталось X из Y».

Встроен в `DeliveryService`: `can_send` → проверка, `record_send` → инкремент, `record_flood_wait` → cooldown. Показывается в `Статус аккаунтов` и перед запуском кампании (шаг 9/9).

## Архитектура

```
app/
  bot/              # handlers (wizard, accounts, campaigns...), keyboards
  providers/        # telegram_user, instagram_personal, facebook_personal, whatsapp_personal, email, tiktok
  services/         # account_rate_limiter, account_manager, delivery_service, campaign_service
  domain/           # models, statuses
  storage/          # SQLite (owner_id изоляция)
  utils/            # text_variation
main.py
requirements.txt
.env.example
```

## Что работает из коробки

- Подключение Telegram личного через Telethon, 9 шагов мастера с country/city, ввод количества/списка, отправка с лимитами, статус прогрева, логирование, черновики — ✅
- Instagram/Messenger/WhatsApp — личные провайдеры с сессиями (если библиотеки не установлены — честный `service_error` с инструкцией `pip install`, не заглушка «не подключён» без попытки)
- Вариации текста, несколько аккаунтов на канал (`account_manager`), статистика `sent/failed/delayed`

## Что не делать (соблюдено)

- Нет заглушек всегда «не подключён» — реальная проверка сессии/токена
- Не только Business API — личные аккаунты приоритет
- Мастер не ломается после числа
- Сессии и `.env` в `.gitignore`

## Тесты

`pytest -q` 89 passed — лимитер, отправка от личного, цели 5-10/100, FloodWait, меню, статистика, безопасность.

## Запуск в Codespaces

Откройте репо в Codespaces → `.devcontainer` автоматом `pip install` → `python main.py` → подключите аккаунты.
