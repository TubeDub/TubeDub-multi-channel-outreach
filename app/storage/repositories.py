import aiosqlite
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from app.domain.models import Campaign, Contact, Delivery, ActivityEvent, Setting, ProviderConnection, User, PaymentRequest

def _now():
    return datetime.now(timezone.utc).isoformat()

# Campaign repo
class CampaignRepo:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def create(self, c: Campaign) -> Campaign:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            now = _now()
            # ensure recipients_json
            rec = getattr(c, 'recipients_json', '[]')
            cur = await db.execute(
                """INSERT INTO campaigns (owner_id, platform, campaign_type, country, city, audience_source, audience_mode, requested_limit, message_text, link, schedule_at, status, created_at, updated_at, idempotency_key, recipients_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (c.owner_id, c.platform, c.campaign_type, c.country, c.city, c.audience_source, c.audience_mode, c.requested_limit, c.message_text, c.link, c.schedule_at, c.status, now, now, c.idempotency_key, rec)
            )
            await db.commit()
            c.id = cur.lastrowid
            c.created_at = now
            c.updated_at = now
            return c

    async def get(self, campaign_id: int) -> Optional[Campaign]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM campaigns WHERE id=?", (campaign_id,))
            row = await cur.fetchone()
            if not row:
                return None
            return self._row_to_campaign(row)

    async def list_by_owner(self, owner_id: int, limit=50, offset=0) -> List[Campaign]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM campaigns WHERE owner_id=? ORDER BY id DESC LIMIT ? OFFSET ?", (owner_id, limit, offset))
            rows = await cur.fetchall()
            return [self._row_to_campaign(r) for r in rows]

    async def count_by_owner(self, owner_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("SELECT COUNT(*) FROM campaigns WHERE owner_id=?", (owner_id,))
            row = await cur.fetchone()
            return row[0]

    async def update(self, c: Campaign) -> Campaign:
        async with aiosqlite.connect(self.db_path) as db:
            now = _now()
            rec = getattr(c, 'recipients_json', '[]')
            await db.execute(
                """UPDATE campaigns SET platform=?, campaign_type=?, country=?, city=?, audience_source=?, audience_mode=?, requested_limit=?, message_text=?, link=?, schedule_at=?, status=?, updated_at=?, idempotency_key=?, recipients_json=? WHERE id=?""",
                (c.platform, c.campaign_type, c.country, c.city, c.audience_source, c.audience_mode, c.requested_limit, c.message_text, c.link, c.schedule_at, c.status, now, c.idempotency_key, rec, c.id)
            )
            await db.commit()
            c.updated_at = now
            return c

    async def delete(self, campaign_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM campaigns WHERE id=?", (campaign_id,))
            await db.commit()

    def _row_to_campaign(self, row):
        # handle optional recipients_json column for backward compat
        try:
            rec = row["recipients_json"]
        except:
            rec = "[]"
        return Campaign(
            id=row["id"],
            owner_id=row["owner_id"],
            platform=row["platform"],
            campaign_type=row["campaign_type"],
            country=row["country"] or "",
            city=row["city"] or "",
            audience_source=row["audience_source"] or "bot_subscribers",
            audience_mode=row["audience_mode"] or "subscribers",
            requested_limit=row["requested_limit"] or 0,
            message_text=row["message_text"] or "",
            link=row["link"] or "",
            schedule_at=row["schedule_at"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            idempotency_key=row["idempotency_key"],
            recipients_json=rec or "[]",
        )

class ContactRepo:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def upsert(self, contact: Contact):
        async with aiosqlite.connect(self.db_path) as db:
            now = _now()
            await db.execute(
                """INSERT INTO contacts (owner_id, provider, external_id, consent_status, consent_source, consent_at, unsubscribed_at, display_name)
                   VALUES (?,?,?,?,?,?,?,?)
                   ON CONFLICT(owner_id, provider, external_id) DO UPDATE SET consent_status=excluded.consent_status, consent_source=excluded.consent_source, consent_at=excluded.consent_at, unsubscribed_at=excluded.unsubscribed_at, display_name=excluded.display_name
                """,
                (contact.owner_id, contact.provider, contact.external_id, contact.consent_status, contact.consent_source, contact.consent_at or now, contact.unsubscribed_at, contact.display_name)
            )
            await db.commit()

    async def get(self, owner_id: int, provider: str, external_id: str) -> Optional[Contact]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM contacts WHERE owner_id=? AND provider=? AND external_id=?", (owner_id, provider, external_id))
            row = await cur.fetchone()
            if not row:
                return None
            return Contact(id=row["id"], owner_id=row["owner_id"], provider=row["provider"], external_id=row["external_id"], consent_status=row["consent_status"], consent_source=row["consent_source"], consent_at=row["consent_at"], unsubscribed_at=row["unsubscribed_at"], display_name=row["display_name"])

    async def list_consented(self, owner_id: int, provider: str) -> List[Contact]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM contacts WHERE owner_id=? AND provider=? AND consent_status='granted' AND unsubscribed_at IS NULL", (owner_id, provider))
            rows = await cur.fetchall()
            return [Contact(id=r["id"], owner_id=r["owner_id"], provider=r["provider"], external_id=r["external_id"], consent_status=r["consent_status"], consent_source=r["consent_source"], consent_at=r["consent_at"], unsubscribed_at=r["unsubscribed_at"], display_name=r["display_name"]) for r in rows]

    async def set_unsubscribed(self, owner_id: int, provider: str, external_id: str):
        async with aiosqlite.connect(self.db_path) as db:
            now = _now()
            await db.execute("UPDATE contacts SET consent_status='revoked', unsubscribed_at=? WHERE owner_id=? AND provider=? AND external_id=?", (now, owner_id, provider, external_id))
            await db.commit()

class DeliveryRepo:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def create_many(self, deliveries: List[Delivery]):
        if not deliveries:
            return
        async with aiosqlite.connect(self.db_path) as db:
            now = _now()
            for d in deliveries:
                # пробуем с next_retry_at, fallback без неё для старых БД
                try:
                    await db.execute(
                        "INSERT INTO deliveries (campaign_id, recipient, status, attempts, provider_message_id, error_code, error_text, created_at, updated_at, next_retry_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (d.campaign_id, d.recipient, d.status, d.attempts, d.provider_message_id, d.error_code, d.error_text, now, now, getattr(d, 'next_retry_at', None))
                    )
                except Exception:
                    await db.execute(
                        "INSERT INTO deliveries (campaign_id, recipient, status, attempts, provider_message_id, error_code, error_text, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                        (d.campaign_id, d.recipient, d.status, d.attempts, d.provider_message_id, d.error_code, d.error_text, now, now)
                    )
            await db.commit()

    async def list_by_campaign(self, campaign_id: int) -> List[Delivery]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM deliveries WHERE campaign_id=? ORDER BY id", (campaign_id,))
            rows = await cur.fetchall()
            res = []
            for r in rows:
                try:
                    nr = r["next_retry_at"]
                except:
                    nr = None
                res.append(Delivery(id=r["id"], campaign_id=r["campaign_id"], recipient=r["recipient"], status=r["status"], attempts=r["attempts"], provider_message_id=r["provider_message_id"], error_code=r["error_code"], error_text=r["error_text"], created_at=r["created_at"], updated_at=r["updated_at"], next_retry_at=nr))
            return res

    async def stats(self, campaign_id: int) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("SELECT status, COUNT(*) FROM deliveries WHERE campaign_id=? GROUP BY status", (campaign_id,))
            rows = await cur.fetchall()
            return {r[0]: r[1] for r in rows}

    async def detailed_stats(self, campaign: 'Campaign') -> dict:
        """Честная статистика по ТЗ §4: вычисляется по сохранённым результатам, не по заранее заданным числам."""
        base = await self.stats(campaign.id) if campaign.id else {}
        # campaign.requested_limit = выбрано
        # available = лимит запроса / отфильтрованная аудитория (пока = количество deliveries)
        total = sum(base.values())
        # mapping to required fields
        return {
            "selected": campaign.requested_limit or total,
            "available": total,
            "pending": base.get("pending", 0) + base.get("queued", 0),
            "sending": base.get("sending", 0) + base.get("running", 0),
            "sent": base.get("sent", 0),
            "delivered": base.get("delivered", 0),
            "failed": base.get("failed", 0),
            "skipped": base.get("skipped", 0),
            "retry": base.get("retry", 0),
            "cancelled": base.get("cancelled", 0),
            "total": total,
        }

    async def update_status(self, delivery_id: int, status: str, attempts: int = None, provider_message_id: str = None, error_code: str = None, error_text: str = None):
        async with aiosqlite.connect(self.db_path) as db:
            now = _now()
            # fetch current
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM deliveries WHERE id=?", (delivery_id,))
            row = await cur.fetchone()
            if not row:
                return
            new_attempts = attempts if attempts is not None else row["attempts"]
            await db.execute("UPDATE deliveries SET status=?, attempts=?, provider_message_id=?, error_code=?, error_text=?, updated_at=? WHERE id=?",
                             (status, new_attempts, provider_message_id or row["provider_message_id"], error_code, error_text, now, delivery_id))
            await db.commit()

class ActivityRepo:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def log(self, owner_id: int, campaign_id: Optional[int], event: str, details: str = ""):
        async with aiosqlite.connect(self.db_path) as db:
            now = _now()
            await db.execute("INSERT INTO activity (owner_id, campaign_id, event, details, created_at) VALUES (?,?,?,?,?)", (owner_id, campaign_id, event, details, now))
            await db.commit()

    async def list_by_owner(self, owner_id: int, limit=50, offset=0) -> List[ActivityEvent]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM activity WHERE owner_id=? ORDER BY id DESC LIMIT ? OFFSET ?", (owner_id, limit, offset))
            rows = await cur.fetchall()
            return [ActivityEvent(id=r["id"], owner_id=r["owner_id"], campaign_id=r["campaign_id"], event=r["event"], details=r["details"], created_at=r["created_at"]) for r in rows]

    async def list_by_campaign(self, campaign_id: int) -> List[ActivityEvent]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM activity WHERE campaign_id=? ORDER BY id DESC LIMIT 100", (campaign_id,))
            rows = await cur.fetchall()
            return [ActivityEvent(id=r["id"], owner_id=r["owner_id"], campaign_id=r["campaign_id"], event=r["event"], details=r["details"], created_at=r["created_at"]) for r in rows]

class SettingsRepo:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def get(self, owner_id: int) -> Setting:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM settings WHERE owner_id=?", (owner_id,))
            row = await cur.fetchone()
            if not row:
                return Setting(owner_id=owner_id)
            # handle optional language column
            try:
                lang = row["language"]
            except:
                lang = "ru"
            return Setting(owner_id=row["owner_id"], default_country=row["default_country"] or "", timezone=row["timezone"] or "Europe/Kiev", test_mode=row["test_mode"], notifications=row["notifications"], queue_limit=row["queue_limit"], language=lang or "ru")

    async def upsert(self, s: Setting):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""INSERT INTO settings (owner_id, default_country, timezone, test_mode, notifications, queue_limit, language) VALUES (?,?,?,?,?,?,?)
                                ON CONFLICT(owner_id) DO UPDATE SET default_country=excluded.default_country, timezone=excluded.timezone, test_mode=excluded.test_mode, notifications=excluded.notifications, queue_limit=excluded.queue_limit, language=excluded.language
                             """, (s.owner_id, s.default_country, s.timezone, s.test_mode, s.notifications, s.queue_limit, s.language))
            await db.commit()

class ProviderConnectionRepo:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def get(self, owner_id: int, provider: str) -> Optional[ProviderConnection]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM provider_connections WHERE owner_id=? AND provider=?", (owner_id, provider))
            row = await cur.fetchone()
            if not row:
                return None
            return ProviderConnection(id=row["id"], owner_id=row["owner_id"], provider=row["provider"], status=row["status"], meta=row["meta"], updated_at=row["updated_at"])

    async def upsert(self, pc: ProviderConnection):
        async with aiosqlite.connect(self.db_path) as db:
            now = _now()
            await db.execute("""INSERT INTO provider_connections (owner_id, provider, status, meta, updated_at) VALUES (?,?,?,?,?)
                                ON CONFLICT(owner_id, provider) DO UPDATE SET status=excluded.status, meta=excluded.meta, updated_at=excluded.updated_at
                             """, (pc.owner_id, pc.provider, pc.status, pc.meta, now))
            await db.commit()

    async def list_by_owner(self, owner_id: int) -> List[ProviderConnection]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM provider_connections WHERE owner_id=?", (owner_id,))
            rows = await cur.fetchall()
            return [ProviderConnection(id=r["id"], owner_id=r["owner_id"], provider=r["provider"], status=r["status"], meta=r["meta"], updated_at=r["updated_at"]) for r in rows]

class UserRepo:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def get(self, user_id: int) -> Optional[User]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
            row = await cur.fetchone()
            if not row:
                return None
            try:
                lang = row["language"]
            except:
                lang = "ru"
            return User(user_id=row["user_id"], username=row["username"] or "", first_name=row["first_name"] or "", created_at=row["created_at"], free_used=row["free_used"], free_total=row["free_total"], subscription_status=row["subscription_status"], subscription_expires_at=row["subscription_expires_at"], updated_at=row["updated_at"], language=lang or "ru")

    async def get_or_create(self, user_id: int, username: str = "", first_name: str = "") -> User:
        existing = await self.get(user_id)
        if existing:
            # update username/first_name if changed
            if username != existing.username or first_name != existing.first_name:
                existing.username = username or existing.username
                existing.first_name = first_name or existing.first_name
                await self.upsert(existing)
            return existing
        now = _now()
        user = User(user_id=user_id, username=username or "", first_name=first_name or "", created_at=now, free_used=0, free_total=10, subscription_status="free", updated_at=now)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT INTO users (user_id, username, first_name, created_at, free_used, free_total, subscription_status, subscription_expires_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                             (user.user_id, user.username, user.first_name, user.created_at, user.free_used, user.free_total, user.subscription_status, user.subscription_expires_at, user.updated_at))
            await db.commit()
        return user

    async def upsert(self, user: User):
        async with aiosqlite.connect(self.db_path) as db:
            now = _now()
            user.updated_at = now
            # handle language column optionally existing
            try:
                await db.execute("""INSERT INTO users (user_id, username, first_name, created_at, free_used, free_total, subscription_status, subscription_expires_at, updated_at, language)
                                    VALUES (?,?,?,?,?,?,?,?,?,?)
                                    ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name, free_used=excluded.free_used, free_total=excluded.free_total, subscription_status=excluded.subscription_status, subscription_expires_at=excluded.subscription_expires_at, updated_at=excluded.updated_at, language=excluded.language
                                 """, (user.user_id, user.username, user.first_name, user.created_at, user.free_used, user.free_total, user.subscription_status, user.subscription_expires_at, user.updated_at, getattr(user, 'language', 'ru')))
            except Exception:
                # fallback without language if migration not yet
                await db.execute("""INSERT INTO users (user_id, username, first_name, created_at, free_used, free_total, subscription_status, subscription_expires_at, updated_at)
                                    VALUES (?,?,?,?,?,?,?,?,?)
                                    ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name, free_used=excluded.free_used, free_total=excluded.free_total, subscription_status=excluded.subscription_status, subscription_expires_at=excluded.subscription_expires_at, updated_at=excluded.updated_at
                                 """, (user.user_id, user.username, user.first_name, user.created_at, user.free_used, user.free_total, user.subscription_status, user.subscription_expires_at, user.updated_at))
            await db.commit()

    async def increment_free_used(self, user_id: int) -> User:
        """Атомарное увеличение с защитой от отрицательных и конкурентных запросов"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("BEGIN IMMEDIATE")
            try:
                cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
                row = await cur.fetchone()
                if not row:
                    await db.execute("ROLLBACK")
                    return None
                free_used = row["free_used"] or 0
                free_total = row["free_total"] or 10
                # защита от отрицательных и превышения — но позволяем > free_total если подписка активна? Логика в subscription_service
                if free_used < 0:
                    free_used = 0
                # инкремент только если не превышен ли это проверяется вне, здесь просто +1 с проверкой не уйти в минус
                new_used = free_used + 1
                if new_used < 0:
                    new_used = 0
                now = _now()
                await db.execute("UPDATE users SET free_used=?, updated_at=? WHERE user_id=?", (new_used, now, user_id))
                await db.commit()
                cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
                row = await cur.fetchone()
                try:
                    lang = row["language"]
                except:
                    lang = "ru"
                return User(user_id=row["user_id"], username=row["username"] or "", first_name=row["first_name"] or "", created_at=row["created_at"], free_used=row["free_used"], free_total=row["free_total"], subscription_status=row["subscription_status"], subscription_expires_at=row["subscription_expires_at"], updated_at=row["updated_at"], language=lang or "ru")
            except Exception:
                await db.execute("ROLLBACK")
                raise

    async def set_subscription(self, user_id: int, status: str, expires_at: Optional[str]):
        async with aiosqlite.connect(self.db_path) as db:
            now = _now()
            await db.execute("UPDATE users SET subscription_status=?, subscription_expires_at=?, updated_at=? WHERE user_id=?", (status, expires_at, now, user_id))
            await db.commit()

class PaymentRequestRepo:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def create(self, pr: PaymentRequest) -> PaymentRequest:
        async with aiosqlite.connect(self.db_path) as db:
            now = _now()
            pr.created_at = now
            cur = await db.execute("INSERT INTO payment_requests (user_id, created_at, status, amount_usd, period_days, payment_mode, card_last4, admin_id, reviewed_at, details) VALUES (?,?,?,?,?,?,?,?,?,?)",
                                   (pr.user_id, pr.created_at, pr.status, pr.amount_usd, pr.period_days, pr.payment_mode, pr.card_last4, pr.admin_id, pr.reviewed_at, pr.details))
            await db.commit()
            pr.id = cur.lastrowid
            return pr

    async def get(self, request_id: int) -> Optional[PaymentRequest]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM payment_requests WHERE id=?", (request_id,))
            row = await cur.fetchone()
            if not row:
                return None
            return PaymentRequest(id=row["id"], user_id=row["user_id"], created_at=row["created_at"], status=row["status"], amount_usd=row["amount_usd"], period_days=row["period_days"], payment_mode=row["payment_mode"], card_last4=row["card_last4"] or "", admin_id=row["admin_id"], reviewed_at=row["reviewed_at"], details=row["details"] or "")

    async def list_by_user(self, user_id: int, limit=20) -> List[PaymentRequest]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM payment_requests WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit))
            rows = await cur.fetchall()
            return [PaymentRequest(id=r["id"], user_id=r["user_id"], created_at=r["created_at"], status=r["status"], amount_usd=r["amount_usd"], period_days=r["period_days"], payment_mode=r["payment_mode"], card_last4=r["card_last4"] or "", admin_id=r["admin_id"], reviewed_at=r["reviewed_at"], details=r["details"] or "") for r in rows]

    async def list_pending(self, limit=50) -> List[PaymentRequest]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM payment_requests WHERE status='pending' ORDER BY id ASC LIMIT ?", (limit,))
            rows = await cur.fetchall()
            return [PaymentRequest(id=r["id"], user_id=r["user_id"], created_at=r["created_at"], status=r["status"], amount_usd=r["amount_usd"], period_days=r["period_days"], payment_mode=r["payment_mode"], card_last4=r["card_last4"] or "", admin_id=r["admin_id"], reviewed_at=r["reviewed_at"], details=r["details"] or "") for r in rows]

    async def update_status(self, request_id: int, status: str, admin_id: int, details: str = ""):
        async with aiosqlite.connect(self.db_path) as db:
            now = _now()
            await db.execute("UPDATE payment_requests SET status=?, admin_id=?, reviewed_at=?, details=? WHERE id=?", (status, admin_id, now, details, request_id))
            await db.commit()

    async def has_pending(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("SELECT COUNT(*) FROM payment_requests WHERE user_id=? AND status='pending'", (user_id,))
            row = await cur.fetchone()
            return row[0] > 0

