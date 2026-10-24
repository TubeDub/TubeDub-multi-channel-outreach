# Миграция

## Откуда
- `TubeDub/multi-channel-outreach` или `multi-channel-outreach-v2-fixed`

## Что мигрируется
- `campaigns` (user_id→owner_id, audience_type→audience_mode, count→requested_limit, message→message_text) + добавления `campaign_type/audience_source/requested_limit/recipients_json` + индексы
- `users` + `payment_requests` (10 бесплатных, подписка)
- `settings.language` + `users.language` + `deliveries.next_retry_at`
- `app/data/countries.py` единый — без дублирования в разных файлах

## Как
```powershell
Copy-Item .env .env.bak
python app/storage/migrations/migrate.py  # делает backups/backup_*.db
python -m pytest -q  # 69 passed
python app.py
```
Повторный запуск безопасен (IF NOT EXISTS + ALTER ADD COLUMN if not exists).

## Откат
```powershell
Copy-Item backups/backup_*.db data/app.db
```

## Проверка
- Старые кампании остаются, новые поля default
- Язык по умолчанию ru, меняется в ⚙️ Настройки → 🌐
- Страна теперь через picker, но старые значения сохранены
- Очередь сохраняется после рестарта
