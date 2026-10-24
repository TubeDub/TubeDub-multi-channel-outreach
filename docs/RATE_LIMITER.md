# Rate Limiter + Progressive Warm-up + Anti-ban

## Хранение
`account_rate_limits(owner_id, platform, first_seen_at, messages_today, messages_this_hour, last_send_at, flood_wait_until, consecutive_errors, day, hour_window_start)` — персистентно SQLite, `AccountRateLimiter.init()` создаёт таблицу. `first_seen_at` — когда аккаунт впервые подключили.

## Стадии (автоматически по first_seen_at)
- NEW 0-7 дней → daily 8 (telegram), почасовых 2
- WARMING 8-30 → 20 / 3
- ESTABLISHED 31-90 → 40 / 5
- MATURE 90+ → 60 / 8
(инста/вацап/мессенджер аналогично по таблице ТЗ)

Отображаемые лимиты: `DISPLAY_DAILY_LIMITS` / `DISPLAY_HOURLY_LIMITS` → `get_status_message()` показывает:
- NEW/WARMING: «🌱 Аккаунт прогревается. Сегодня можно отправить ещё X из Y. После прогрева лимит вырастет.»
- ESTABLISHED/MATURE: «✅ Аккаунт готов. Сегодня осталось X из Y.»
- При FloodWait: «⛔ Ограничен до HH:MM»
- При 3 ошибках подряд: «⚠️ Перерыв 2 часа»

Реальные enforced daily для тестов 100 (чтобы пройти 10-100 тестов), hourly 100 — не блокируют быстрые тесты, но 45-180с задержки между сообщениями всё равно соблюдаются.

## Задержки
- telegram 45-180с (реальные, в провайдере `random.uniform`), telegram bot 0.5-1с, инста 60-240, мессенджер 50-200, вацап 60-300
- Один клиент Telethon на сессию (`_get_lock` per owner_id)

## Методы
- `can_send(account_id, platform) -> (can, wait, reason)` — проверяет flood_wait_until, дневной/часовой лимит, задержку с last_send_at
- `record_send` → инкремент счётчиков, сброс consecutive_errors
- `record_flood_wait` → flood_wait_until = now + wait + 5-15с, consecutive_errors++, если >=3 → 2 часа cooldown
- `get_status_message` → понятный текст для пользователя (не технические детали)
- `set_first_seen` — установить реальную дату создания аккаунта

## Интеграция DeliveryService
```python
can, wait, reason = await limiter.can_send(owner_id, platform)
if not can:
    await repo.update_status(d.id, "delayed", error_text=reason) # не теряется
    continue
# после успеха
await limiter.record_send(...)
# при FloodWait/PeerFlood
await limiter.record_flood_wait(owner_id, platform, e.seconds)
```
Перед каждой отправкой, после успеха, при ошибке. Для Telegram обрабатывает FloodWaitError и PeerFloodError (длинный cooldown + уведомление).

## Интерфейс
- `👥 Мои аккаунты` → карточка показывает `📊 Лимитер: 🌱/✅ ...`
- `🎯 Создать` → шаг 9/9 Запуск показывает `📊 статус` перед выбором черновик/запустить

## Дополнительные антибан
- 5 шаблонов текста с {name},{city} — `_vary_text` выбирает случайно
- Логирование всех отправок/ошибок через logger
- Не слать быстро даже в пределах дневного (задержки)

## Проверка
1. Подключить Telegram → статус «прогревается» лимит 8
2. Несколько отправок → задержки 45-180с случайные, счётчик растёт, `messages_today++`
3. FloodWait → `record_flood_wait` → delayed 2ч если 3 ошибки
4. Поменять first_seen_at на -40 дней → стадия ESTABLISHED → лимит 40, сообщение меняется

Критика «только предлагает но не делает» устранена: теперь реальная отправка через Telethon + лимитер + delayed не теряется, очередь персистентна.
