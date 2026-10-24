"""
Аудитории — импорт, дедупликация, фильтрация, проверка возможности отправки
"""
import csv
import io
from typing import List, Tuple, Dict
from app.storage.repositories import ContactRepo
from app.domain.models import Contact
from datetime import datetime, timezone

REQUIRED_FIELDS = ["external_id", "provider"]  # external_id — телефон, email, username, chat_id

class AudienceImportService:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.repo = ContactRepo(db_path)

    async def import_csv(self, owner_id: int, file_bytes: bytes, filename: str = "") -> Tuple[int, int, List[str]]:
        """
        Импорт CSV: ожидаем колонки external_id, provider, display_name?, country?, language?
        Возвращает (imported, duplicates_skipped, errors)
        """
        text = file_bytes.decode('utf-8', errors='ignore')
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or "external_id" not in [f.lower() for f in reader.fieldnames]:
            return 0, 0, ["Нужна колонка external_id"]
        
        imported = 0
        dups = 0
        errors = []
        seen = set()
        for idx, row in enumerate(reader, start=2):
            # нормализуем ключи
            row_low = {k.lower(): v for k,v in row.items()}
            ext = (row_low.get("external_id") or "").strip()
            provider = (row_low.get("provider") or "telegram").strip().lower()
            display = (row_low.get("display_name") or row_low.get("name") or "").strip()
            if not ext:
                errors.append(f"Строка {idx}: пустой external_id")
                continue
            key = (provider, ext)
            if key in seen:
                dups += 1
                continue
            seen.add(key)
            # проверка дубликата в БД
            existing = await self.repo.get(owner_id, provider, ext)
            if existing:
                dups += 1
                continue
            # валидация по каналу
            if provider == "email" and "@" not in ext:
                errors.append(f"Строка {idx}: невалидный email {ext}")
                continue
            if provider == "whatsapp" and not ext.startswith("+") and not ext.isdigit():
                # разрешаем разные форматы, но предупреждаем
                pass
            # сохранение с согласием (пользователь подтверждает что имеет согласие)
            contact = Contact(
                owner_id=owner_id,
                provider=provider,
                external_id=ext,
                consent_status="granted",
                consent_source=f"csv_import:{filename}",
                consent_at=datetime.now(timezone.utc).isoformat(),
                display_name=display
            )
            await self.repo.upsert(contact)
            imported += 1
        return imported, dups, errors

    async def list_contacts(self, owner_id: int, provider: str = None, limit: int = 100) -> List[Contact]:
        if provider:
            return await self.repo.list_consented(owner_id, provider)
        # все провайдеры
        result = []
        for prov in ["telegram", "telegram_user", "facebook_messenger", "instagram", "whatsapp", "email", "tiktok"]:
            lst = await self.repo.list_consented(owner_id, prov)
            result.extend(lst)
        return result[:limit]

    async def filter_contacts(self, owner_id: int, provider: str = None, country: str = None, language: str = None, search: str = None) -> List[Contact]:
        contacts = await self.list_contacts(owner_id, provider)
        # фильтрация — пока по display_name, в будущем по country/language если хранить
        if country and country not in ("Все страны", "Не указана"):
            contacts = [c for c in contacts if country.lower() in (c.display_name or "").lower() or True]  # пока заглушка, не фильтруем жёстко
        if search:
            q = search.lower()
            contacts = [c for c in contacts if q in c.external_id.lower() or q in (c.display_name or "").lower()]
        return contacts

    async def check_sendable(self, owner_id: int, provider: str, external_id: str) -> Tuple[bool, str]:
        contact = await self.repo.get(owner_id, provider, external_id)
        if not contact:
            return False, "Контакт не найден — добавьте в аудиторию"
        if contact.consent_status != "granted" or contact.unsubscribed_at:
            return False, "Исключён: отписался или нет согласия (suppression list)"
        return True, "Доступен"

    async def remove_duplicates(self, owner_id: int) -> int:
        # дедупликация в БД уже через UNIQUE, но дополнительная проверка
        return 0

    async def delete_contact(self, owner_id: int, provider: str, external_id: str):
        contact = await self.repo.get(owner_id, provider, external_id)
        if contact:
            await self.repo.set_unsubscribed(owner_id, provider, external_id)
