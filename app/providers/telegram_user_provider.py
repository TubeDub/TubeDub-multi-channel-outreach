"""
Telegram User Account Provider (MTProto via Telethon).
Реальный отправитель от личного аккаунта пользователя.
НЕ путать с Telegram Bot API.
"""

import os
import asyncio
import random
from pathlib import Path
from typing import Dict, Any

from telethon import TelegramClient, errors

from app.providers.base import BaseProvider
from app.domain.errors import ProviderError, RateLimitError, ForbiddenError


class TelegramUserProvider(BaseProvider):
    platform = "telegram_user"

    def __init__(self, db_path: str = None, sessions_dir: str = None):
        self.db_path = db_path
        self.api_id = int(os.getenv("TELEGRAM_API_ID", "0") or "0")
        self.api_hash = os.getenv("TELEGRAM_API_HASH", "")
        self.sessions_dir = Path(sessions_dir or os.getenv("SESSIONS_DIR", "./data/sessions"))
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._clients: Dict[int, TelegramClient] = {}
        self._locks: Dict[int, asyncio.Lock] = {}

    def _session_path(self, owner_id: int) -> Path:
        return self.sessions_dir / f"user_{owner_id}.session"

    def _get_lock(self, owner_id: int) -> asyncio.Lock:
        if owner_id not in self._locks:
            self._locks[owner_id] = asyncio.Lock()
        return self._locks[owner_id]

    async def _get_client(self, owner_id: int) -> TelegramClient:
        if owner_id in self._clients and self._clients[owner_id].is_connected():
            return self._clients[owner_id]

        session_file = self._session_path(owner_id)
        client = TelegramClient(
            str(session_file),
            self.api_id,
            self.api_hash,
            device_model="MultiChannel Outreach",
            system_version="1.0",
            app_version="1.0",
        )
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            raise ProviderError(
                "Сессия не авторизована. Нужно пройти вход (телефон + код + 2FA).",
                code="not_authorized",
            )
        self._clients[owner_id] = client
        return client

    async def check_connection(self, owner_id: int = None) -> Dict[str, Any]:
        if not self.api_id or not self.api_hash:
            return {
                "status": "not_connected",
                "hint": "TELEGRAM_API_ID и TELEGRAM_API_HASH не заданы в .env",
                "capabilities": await self.get_capabilities(),
                "next_step": "Добавьте TELEGRAM_API_ID и TELEGRAM_API_HASH в .env (my.telegram.org → API development tools), затем Подключить личный Telegram",
            }
        try:
            client = await self._get_client(owner_id)
            me = await client.get_me()
            # save status to DB for diagnostics
            if self.db_path and owner_id:
                try:
                    from app.storage.repositories import ProviderConnectionRepo
                    from app.domain.models import ProviderConnection
                    repo = ProviderConnectionRepo(self.db_path)
                    await repo.upsert(ProviderConnection(owner_id=owner_id, provider="telegram_user", status="connected", meta=f"@{me.username or me.id} | {me.first_name}"))
                except:
                    pass
            return {
                "status": "connected",
                "hint": f"Личный аккаунт @{me.username or me.id} ({me.first_name})",
                "user": {"id": me.id, "username": me.username, "first_name": me.first_name},
                "capabilities": await self.get_capabilities(),
                "next_step": self.next_step_hint("connected"),
                "account": {"id": me.id, "username": me.username},
            }
        except ProviderError as e:
            return {"status": "not_connected", "hint": str(e), "capabilities": await self.get_capabilities(), "next_step": self.next_step_hint("not_connected")}
        except Exception as e:
            return {"status": "not_connected", "hint": f"Ошибка сессии: {e}", "capabilities": await self.get_capabilities(), "next_step": self.next_step_hint("not_connected")}

    async def get_capabilities(self) -> Dict[str, bool]:
        return {
            "send_message": True,
            "cold_outreach": True,
            "check_connection": True,
            "requires_session": True,
        }

    async def send_message(
        self,
        recipient: str,
        text: str,
        owner_id: int = None,
        delay_range: tuple = (45, 180),
    ) -> Dict[str, Any]:
        if not self.api_id or not self.api_hash:
            raise ProviderError("Telegram API_ID/HASH не настроены (not_connected) — добавьте в .env", code="not_connected")
        if not owner_id:
            raise ProviderError("owner_id обязателен для личного аккаунта", code="no_owner")

        async with self._get_lock(owner_id):
            client = await self._get_client(owner_id)

            # Антибан: рандомизированная задержка 45-120с (настраиваемо)
            delay = random.uniform(*delay_range)
            await asyncio.sleep(delay)

            try:
                entity = await client.get_entity(recipient)
                msg = await client.send_message(entity, text)
                return {
                    "message_id": msg.id,
                    "chat_id": getattr(entity, "id", recipient),
                    "date": msg.date.isoformat() if msg.date else None,
                }
            except errors.FloodWaitError as e:
                wait = e.seconds + random.randint(5, 15)
                raise RateLimitError(
                    f"FloodWait {e.seconds}s",
                    code="flood_wait",
                    retry_after=wait,
                )
            except errors.PeerFloodError:
                raise ForbiddenError(
                    "PEER_FLOOD — аккаунт ограничен. Остановите отправку на этом аккаунте.",
                    code="peer_flood",
                )
            except errors.UserPrivacyRestrictedError:
                raise ForbiddenError("Пользователь ограничил сообщения", code="privacy")
            except errors.UsernameNotOccupiedError:
                raise ProviderError(f"Username {recipient} не существует", code="not_found")
            except errors.UserIsBlockedError:
                raise ForbiddenError("Пользователь заблокировал аккаунт", code="blocked")
            except Exception as e:
                raise ProviderError(str(e), code="send_failed")

    async def publish(self, chat_id: str, text: str, owner_id: int = None) -> Dict[str, Any]:
        return await self.send_message(chat_id, text, owner_id)

    async def disconnect(self, owner_id: int):
        if owner_id in self._clients:
            try:
                await self._clients[owner_id].disconnect()
            except:
                pass
            del self._clients[owner_id]

    async def get_available_dialogs(self, owner_id: int, limit: int = 50):
        try:
            client = await self._get_client(owner_id)
            dialogs = await client.get_dialogs(limit=limit)
            result = []
            for d in dialogs:
                if d.is_user and not getattr(d.entity, 'bot', False) and not getattr(d.entity, 'deleted', False):
                    result.append({"id": d.id, "name": d.name, "username": getattr(d.entity, 'username', None)})
                elif getattr(d, 'is_channel', False) or getattr(d, 'is_group', False):
                    result.append({"id": d.id, "name": d.name, "type": "channel/group"})
            return result
        except:
            return []

    async def validate_campaign(self, campaign) -> tuple[bool, list]:
        errs = []
        if campaign.platform not in ("telegram", "telegram_user"):
            errs.append("Кампания не для Telegram личного аккаунта")
        return (len(errs)==0, errs)
