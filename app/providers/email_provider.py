import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.providers.base import BaseProvider
from app.domain.errors import ProviderError

class EmailProvider(BaseProvider):
    platform = "email"

    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self.host = os.getenv("SMTP_HOST", "")
        self.port = int(os.getenv("SMTP_PORT", "587") or "587")
        self.user = os.getenv("SMTP_USER", "")
        self.password = os.getenv("SMTP_PASSWORD", "")
        self.from_addr = os.getenv("SMTP_FROM", "") or self.user

    async def check_connection(self, owner_id: int = None) -> dict:
        if not self.host or not self.user:
            return {
                "status": "not_connected",
                "hint": "Нужны SMTP_HOST, SMTP_USER, SMTP_PASSWORD, SMTP_FROM (или SendGrid/Mailgun API)",
                "capabilities": await self.get_capabilities(),
                "next_step": "Добавьте SMTP в .env (Gmail: smtp.gmail.com + App Password) → Мои аккаунты → Проверить",
                "required": ["SMTP_HOST","SMTP_USER","SMTP_PASSWORD"],
            }
        # реальная проверка логина (не фейк)
        try:
            import aiosmtplib
            # пробуем подключиться — но не блокируем долго, используем smtplib sync в executor
            import asyncio
            loop = asyncio.get_running_loop()
            def try_login():
                if self.port == 465:
                    server = smtplib.SMTP_SSL(self.host, self.port, timeout=10)
                else:
                    server = smtplib.SMTP(self.host, self.port, timeout=10)
                    server.starttls(context=ssl.create_default_context())
                server.login(self.user, self.password)
                server.quit()
                return True
            await loop.run_in_executor(None, try_login)
            return {"status": "connected", "hint": f"SMTP {self.host}:{self.port} ({self.from_addr}) — логин успешен", "capabilities": await self.get_capabilities(), "next_step": self.next_step_hint("connected")}
        except Exception as e:
            return {"status": "configuration_error", "hint": f"Ошибка SMTP логина: {e}", "capabilities": await self.get_capabilities(), "next_step": self.next_step_hint("configuration_error")}

    async def get_capabilities(self) -> dict:
        return {"send_message": True, "cold_outreach": True, "check_connection": True, "supports_smtp": True, "supports_api": True}

    async def send_message(self, recipient: str, text: str, owner_id: int = None) -> dict:
        if not self.host or not self.user:
            raise ProviderError("Email не подключён: SMTP_HOST/USER/PASSWORD не настроены (not_connected)", code="not_connected")
        if "@" not in recipient:
            raise ProviderError(f"Неверный email {recipient}", code="invalid_recipient")
        import asyncio
        loop = asyncio.get_running_loop()
        def do_send():
            msg = MIMEMultipart()
            msg["From"] = self.from_addr
            msg["To"] = recipient
            msg["Subject"] = "Сообщение от MultiChannel Outreach"
            msg.attach(MIMEText(text, "plain", "utf-8"))
            if self.port == 465:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=15)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=15)
                server.starttls(context=ssl.create_default_context())
            server.login(self.user, self.password)
            server.send_message(msg)
            server.quit()
            return True
        try:
            await loop.run_in_executor(None, do_send)
            return {"message_id": f"email:{recipient}", "recipient": recipient}
        except Exception as e:
            raise ProviderError(f"SMTP отправка не удалась: {e}", code="send_failed")

    async def validate_campaign(self, campaign) -> tuple[bool, list]:
        errs = []
        if campaign.platform != "email":
            errs.append("Кампания не для Email")
        return (len(errs)==0, errs)
