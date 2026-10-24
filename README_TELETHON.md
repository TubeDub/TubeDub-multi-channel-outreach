# Подключение личного Telegram (Telethon)

Получите API ID/HASH:
1. https://my.telegram.org → Log In → API development tools → Create application (App title любой)
2. Скопируйте API ID (число) и API Hash (строка)
3. В .env:
```
TELEGRAM_API_ID=1234567
TELEGRAM_API_HASH=0123456789abcdef0123456789abcdef
SESSIONS_DIR=./data/sessions
```
4. В боте: 👥 Мои аккаунты → Подключить личный Telegram → введите +380... → код из Telegram (приходит в Saved Messages или SMS) → 2FA если включена
5. Сессия сохраняется: `data/sessions/user_{owner_id}.session` — не в git, восстанавливается после перезапуска, проверяется `client.get_me()`
6. Антибан: задержки 45–120с + дневной лимит 30 (новый 5-15, прогретый 20-40), FloodWait +5-15с буфер, PeerFlood → остановить аккаунт
7. Проверка отправителя: `wizard platform=telegram_user` → `TelegramUserProvider` (не Bot API), `rate_limiter` + `delay_range`

Остальные каналы: см. REPORT_TECHNICAL.md §4 — Facebook Messenger (Page token, 24h окно), Instagram (Professional), WhatsApp Cloud API (Cloud API + шаблоны), Email (SMTP), TikTok (недоступно).

Запуск: `pip install -r requirements.txt` (telethon>=1.36.0 + cryptg) → `pytest -q` → `migrate.py` → `python -m app`
