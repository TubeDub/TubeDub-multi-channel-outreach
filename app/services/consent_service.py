from app.storage.repositories import ContactRepo
from app.domain.models import Contact
from datetime import datetime, timezone

class ConsentService:
    def __init__(self, db_path: str):
        self.repo = ContactRepo(db_path)

    async def grant(self, owner_id: int, provider: str, external_id: str, source: str = "bot_start", display_name: str = ""):
        c = Contact(owner_id=owner_id, provider=provider, external_id=str(external_id), consent_status="granted", consent_source=source, consent_at=datetime.now(timezone.utc).isoformat(), display_name=display_name)
        await self.repo.upsert(c)

    async def revoke(self, owner_id: int, provider: str, external_id: str):
        await self.repo.set_unsubscribed(owner_id, provider, str(external_id))

    async def is_consented(self, owner_id: int, provider: str, external_id: str) -> bool:
        contact = await self.repo.get(owner_id, provider, str(external_id))
        if not contact:
            return False
        if contact.consent_status != "granted":
            return False
        if contact.unsubscribed_at:
            return False
        return True

    async def get_audience(self, owner_id: int, provider: str, include_revoked=False):
        if include_revoked:
            # not needed
            pass
        return await self.repo.list_consented(owner_id, provider)
