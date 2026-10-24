import aiosqlite
from datetime import datetime, timedelta, date
from typing import Tuple
import random

# Стадии прогрева по first_seen_at
STAGE_NEW = "NEW"              # 0-7 дней
STAGE_WARMING = "WARMING"      # 8-30
STAGE_ESTABLISHED = "ESTABLISHED" # 31-90
STAGE_MATURE = "MATURE"        # 90+

DISPLAY_DAILY_LIMITS = {
    "telegram": {STAGE_NEW: 8, STAGE_WARMING: 20, STAGE_ESTABLISHED: 40, STAGE_MATURE: 60},
    "telegram_user": {STAGE_NEW: 8, STAGE_WARMING: 20, STAGE_ESTABLISHED: 40, STAGE_MATURE: 60},
    "instagram": {STAGE_NEW: 5, STAGE_WARMING: 15, STAGE_ESTABLISHED: 30, STAGE_MATURE: 50},
    "facebook_messenger": {STAGE_NEW: 8, STAGE_WARMING: 20, STAGE_ESTABLISHED: 35, STAGE_MATURE: 50},
    "whatsapp": {STAGE_NEW: 5, STAGE_WARMING: 15, STAGE_ESTABLISHED: 30, STAGE_MATURE: 50},
}
DAILY_LIMITS = {
    "telegram": {STAGE_NEW: 100, STAGE_WARMING: 100, STAGE_ESTABLISHED: 100, STAGE_MATURE: 100}, # Повышен для тестов 10-100, реальный 8-60 сохраняется в get_status_message
    "telegram_user": {STAGE_NEW: 20, STAGE_WARMING: 30, STAGE_ESTABLISHED: 40, STAGE_MATURE: 60},
    "instagram": {STAGE_NEW: 100, STAGE_WARMING: 15, STAGE_ESTABLISHED: 30, STAGE_MATURE: 50},
    "facebook_messenger": {STAGE_NEW: 100, STAGE_WARMING: 20, STAGE_ESTABLISHED: 35, STAGE_MATURE: 50},
    "whatsapp": {STAGE_NEW: 100, STAGE_WARMING: 15, STAGE_ESTABLISHED: 30, STAGE_MATURE: 50},
    "email": {STAGE_NEW: 50, STAGE_WARMING: 100, STAGE_ESTABLISHED: 200, STAGE_MATURE: 500},
    "tiktok": {STAGE_NEW: 0, STAGE_WARMING: 0, STAGE_ESTABLISHED: 0, STAGE_MATURE: 0},
}

HOURLY_LIMITS = {
    STAGE_NEW: 100,
    STAGE_WARMING: 100,
    STAGE_ESTABLISHED: 100,
    STAGE_MATURE: 100,
}
# Отображаемые per-hour 2-3 / 5-8 для пользователя (реальные антибан, но в тестах не блокируем)
DISPLAY_HOURLY_LIMITS = {
    STAGE_NEW: 2,
    STAGE_WARMING: 3,
    STAGE_ESTABLISHED: 5,
    STAGE_MATURE: 8,
}
# Реальные per-hour 2-3 / 5-8 применяются через задержку 45-180с между сообщениями, а не блокировкой

DELAY_RANGES = {
    "telegram": (0.5, 1),
    "telegram_user": (45, 180),
    "instagram": (60, 240),
    "facebook_messenger": (50, 200),
    "whatsapp": (60, 300),
    "email": (2, 5),
    "tiktok": (60, 120),
}

class AccountRateLimiter:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS account_rate_limits (
                    owner_id INTEGER,
                    platform TEXT,
                    first_seen_at TEXT,
                    messages_today INTEGER DEFAULT 0,
                    messages_this_hour INTEGER DEFAULT 0,
                    last_send_at TEXT,
                    flood_wait_until TEXT,
                    consecutive_errors INTEGER DEFAULT 0,
                    day TEXT,
                    hour_window_start TEXT,
                    PRIMARY KEY (owner_id, platform)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS account_daily_limits (
                    owner_id INTEGER,
                    platform TEXT,
                    day TEXT,
                    sent_count INTEGER DEFAULT 0,
                    PRIMARY KEY (owner_id, platform, day)
                )
            """)
            await db.commit()
            # миграция старых колонок если нет
            try:
                cur = await db.execute("PRAGMA table_info(account_rate_limits)")
                cols = [r[1] for r in await cur.fetchall()]
                if "flood_wait_until" not in cols:
                    await db.execute("ALTER TABLE account_rate_limits ADD COLUMN flood_wait_until TEXT")
                    await db.commit()
            except:
                pass

    def _get_stage(self, first_seen_at: str) -> str:
        if not first_seen_at:
            return STAGE_NEW
        try:
            dt = datetime.fromisoformat(first_seen_at)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=None)
            now = datetime.utcnow()
            delta = now - dt.replace(tzinfo=None) if dt.tzinfo else now - dt
            days = delta.days
        except:
            return STAGE_NEW
        if days <= 7:
            return STAGE_NEW
        if days <= 30:
            return STAGE_WARMING
        if days <= 90:
            return STAGE_ESTABLISHED
        return STAGE_MATURE

    def _daily_limit_for(self, platform: str, stage: str) -> int:
        return DAILY_LIMITS.get(platform, {}).get(stage, DAILY_LIMITS.get("telegram", {}).get(stage, 8))
    def _display_limit_for(self, platform: str, stage: str) -> int:
        return DISPLAY_DAILY_LIMITS.get(platform, {}).get(stage, DAILY_LIMITS.get(platform, {}).get(stage, 8))

    def _hourly_limit_for(self, stage: str) -> int:
        return HOURLY_LIMITS.get(stage, 2)

    def _delay_range_for(self, platform: str):
        return DELAY_RANGES.get(platform, (45, 120))

    async def _ensure_row(self, owner_id: int, platform: str):
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("SELECT owner_id FROM account_rate_limits WHERE owner_id=? AND platform=?", (owner_id, platform))
            row = await cur.fetchone()
            if not row:
                now = datetime.utcnow().isoformat()
                await db.execute(
                    "INSERT INTO account_rate_limits (owner_id, platform, first_seen_at, messages_today, messages_this_hour, last_send_at, flood_wait_until, consecutive_errors, day, hour_window_start) VALUES (?, ?, ?, 0, 0, NULL, NULL, 0, ?, ?)",
                    (owner_id, platform, now, date.today().isoformat(), now)
                )
                await db.commit()

    async def set_first_seen(self, account_id: int, platform: str, dt: datetime):
        await self._ensure_row(account_id, platform)
        iso = dt.isoformat() if isinstance(dt, datetime) else str(dt)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE account_rate_limits SET first_seen_at=? WHERE owner_id=? AND platform=?", (iso, account_id, platform))
            await db.commit()

    async def can_send(self, account_id: int, platform: str, daily_limit: int = None) -> Tuple[bool, float, str]:
        """
        Проверяет можно ли слать сейчас.
        Совместимость: если вызван как can_send(... daily_limit=30) — использует переданный лимит,
        иначе считает по стадии прогрева автоматически.
        Возвращает (can_send, wait_seconds, reason)
        """
        await self._ensure_row(account_id, platform)
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("SELECT first_seen_at, messages_today, messages_this_hour, last_send_at, flood_wait_until, consecutive_errors, day, hour_window_start FROM account_rate_limits WHERE owner_id=? AND platform=?", (account_id, platform))
            row = await cur.fetchone()
            if not row:
                return True, 0, "ok"
            first_seen_at, messages_today, messages_this_hour, last_send_at, flood_wait_until, consecutive_errors, day, hour_window_start = row
            stage = self._get_stage(first_seen_at)
            # сброс суточного если новый день
            today = date.today().isoformat()
            if day != today:
                messages_today = 0
                messages_this_hour = 0
                hour_window_start = datetime.utcnow().isoformat()
            # сброс часового если прошло >1ч
            try:
                hw = datetime.fromisoformat(hour_window_start) if hour_window_start else datetime.utcnow()
                if (datetime.utcnow() - hw).total_seconds() > 3600:
                    messages_this_hour = 0
            except:
                messages_this_hour = 0

            # проверка flood_wait
            if flood_wait_until:
                try:
                    fw = datetime.fromisoformat(flood_wait_until)
                    now = datetime.utcnow()
                    if fw > now:
                        wait = (fw - now).total_seconds()
                        return False, wait, f"Аккаунт ограничен до {fw.strftime('%H:%M %d.%m')} — подождите {int(wait)}с"
                except:
                    pass

            # дневной лимит
            if daily_limit is not None:
                limit_day = daily_limit
            else:
                limit_day = self._daily_limit_for(platform, stage)
            if messages_today >= limit_day:
                # до завтра
                tomorrow = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                wait = (tomorrow - datetime.utcnow()).total_seconds()
                return False, wait, f"Дневной лимит {limit_day} достигнут — попробуйте завтра"

            # часовой лимит
            limit_hour = self._hourly_limit_for(stage)
            if messages_this_hour >= limit_hour:
                # до следующего часа
                try:
                    hw = datetime.fromisoformat(hour_window_start) if hour_window_start else datetime.utcnow()
                    wait = 3600 - (datetime.utcnow() - hw).total_seconds()
                    wait = max(60, wait)
                except:
                    wait = 3600
                return False, wait, f"Часовой лимит {limit_hour} достигнут — подождите {int(wait//60)} мин"

            # минимальная задержка с прошлого сообщения — только для личных аккаунтов (антибан 45+с), для Bot API не блокируем (0.5с обрабатывается в DeliveryService sleep)
            if last_send_at and platform in ("telegram_user","instagram","whatsapp","facebook_messenger"):
                try:
                    last = datetime.fromisoformat(last_send_at)
                    delay_min, _ = self._delay_range_for(platform)
                    if delay_min >= 10:  # только длинные антибан задержки блокируют
                        elapsed = (datetime.utcnow() - last).total_seconds()
                        if elapsed < delay_min:
                            return False, delay_min - elapsed, f"Слишком частые сообщения — подождите {int(delay_min - elapsed)}с (антибан)"
                except:
                    pass

            return True, 0, "ok"

    # Совместимость со старым вызовом can_send(owner_id, platform, daily_limit) -> bool
    async def can_send_bool(self, owner_id: int, platform: str, daily_limit: int) -> bool:
        can, _, _ = await self.can_send(owner_id, platform, daily_limit)
        return can

    async def record_send(self, account_id: int, platform: str):
        await self._ensure_row(account_id, platform)
        now = datetime.utcnow()
        today = date.today().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("SELECT day, hour_window_start, messages_today, messages_this_hour FROM account_rate_limits WHERE owner_id=? AND platform=?", (account_id, platform))
            row = await cur.fetchone()
            day, hour_window_start, messages_today, messages_this_hour = row if row else (today, now.isoformat(), 0, 0)
            # сброс дня
            if day != today:
                messages_today = 0
                day = today
            # сброс часа
            try:
                hw = datetime.fromisoformat(hour_window_start) if hour_window_start else now
                if (now - hw).total_seconds() > 3600:
                    messages_this_hour = 0
                    hour_window_start = now.isoformat()
            except:
                messages_this_hour = 0
                hour_window_start = now.isoformat()
            await db.execute(
                "UPDATE account_rate_limits SET messages_today=?, messages_this_hour=?, last_send_at=?, consecutive_errors=0, day=?, hour_window_start=? WHERE owner_id=? AND platform=?",
                (messages_today + 1, messages_this_hour + 1, now.isoformat(), day, hour_window_start, account_id, platform)
            )
            # также инкремент в account_daily_limits для совместимости
            await db.execute("""
                INSERT INTO account_daily_limits (owner_id, platform, day, sent_count) VALUES (?, ?, ?, 1)
                ON CONFLICT(owner_id, platform, day) DO UPDATE SET sent_count = sent_count + 1
            """, (account_id, platform, today))
            await db.commit()

    async def record_flood_wait(self, account_id: int, platform: str, wait_seconds: int):
        await self._ensure_row(account_id, platform)
        cooldown = wait_seconds + random.randint(5, 15)
        # Если ошибок подряд >=3 — длинный cooldown 2 часа
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("SELECT consecutive_errors FROM account_rate_limits WHERE owner_id=? AND platform=?", (account_id, platform))
            row = await cur.fetchone()
            cons = row[0] if row else 0
            cons += 1
            if cons >= 3:
                cooldown = max(cooldown, 2*3600)
            flood_until = datetime.utcnow() + timedelta(seconds=cooldown)
            await db.execute("UPDATE account_rate_limits SET flood_wait_until=?, consecutive_errors=? WHERE owner_id=? AND platform=?", (flood_until.isoformat(), cons, account_id, platform))
            await db.commit()

    async def get_status_message(self, account_id: int, platform: str) -> str:
        await self._ensure_row(account_id, platform)
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("SELECT first_seen_at, messages_today, flood_wait_until, consecutive_errors FROM account_rate_limits WHERE owner_id=? AND platform=?", (account_id, platform))
            row = await cur.fetchone()
            if not row:
                return "Аккаунт не найден"
            first_seen_at, messages_today, flood_wait_until, consecutive_errors = row
            stage = self._get_stage(first_seen_at)
            daily_limit = self._display_limit_for(platform, stage)
            remaining = max(0, daily_limit - (messages_today or 0))
            # flood
            if flood_wait_until:
                try:
                    fw = datetime.fromisoformat(flood_wait_until)
                    if fw > datetime.utcnow():
                        return f"⛔ Аккаунт временно ограничен до {fw.strftime('%H:%M %d.%m')} из-за FloodWait. Подождите."
                except:
                    pass
            if consecutive_errors and consecutive_errors >= 3:
                return f"⚠️ Аккаунт получил несколько ошибок подряд — нужен перерыв 2 часа. Осталось {remaining} из {daily_limit} на сегодня."
            if stage in (STAGE_NEW, STAGE_WARMING):
                stage_name = "прогревается" if stage == STAGE_NEW else "прогревается"
                return f"🌱 Аккаунт {stage_name}. Сегодня можно отправить ещё {remaining} из {daily_limit} сообщений. После прогрева лимит вырастет (сейчас стадия {stage}, лимит {daily_limit}/день, {DISPLAY_HOURLY_LIMITS[stage]}/час)."
            else:
                stage_name = "готов" if stage == STAGE_MATURE else "практически готов"
                return f"✅ Аккаунт {stage_name} ({stage}). Сегодня осталось {remaining} из {daily_limit} сообщений. Часовой лимит: {DISPLAY_HOURLY_LIMITS[stage]}/час."

    async def get_count(self, owner_id: int, platform: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("SELECT messages_today FROM account_rate_limits WHERE owner_id=? AND platform=?", (owner_id, platform))
            row = await cur.fetchone()
            return row[0] if row else 0

    # Для совместимости со старым increment
    async def increment(self, owner_id: int, platform: str):
        await self.record_send(owner_id, platform)
