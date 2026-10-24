import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = os.getenv("DATABASE_PATH", "./data/app.db")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID", "")

# Provider envs (optional)
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = os.getenv("SMTP_PORT", "587")
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")

# Telegram User Account (Telethon) — отдельный от бота
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID", "")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE", "")

# Payment / Subscription
PAYMENT_MODE = os.getenv("PAYMENT_MODE", "manual_placeholder")
SUBSCRIPTION_PRICE_USD = float(os.getenv("SUBSCRIPTION_PRICE_USD", "1") or "1")
SUBSCRIPTION_PERIOD_DAYS = int(os.getenv("SUBSCRIPTION_PERIOD_DAYS", "30") or "30")
PAYMENT_CARD_NUMBER = os.getenv("PAYMENT_CARD_NUMBER", "")
PAYMENT_CARD_HOLDER = os.getenv("PAYMENT_CARD_HOLDER", "")

def get_database_path() -> str:
    return DATABASE_PATH

def get_token() -> str:
    return TELEGRAM_BOT_TOKEN

def is_token_configured() -> bool:
    return bool(TELEGRAM_BOT_TOKEN and len(TELEGRAM_BOT_TOKEN) > 10)

def mask_token(token: str) -> str:
    if not token:
        return "не настроен"
    if len(token) < 8:
        return "***"
    return token[:4] + "***" + token[-4:]

def mask_card_number(card: str) -> str:
    if not card:
        return "не настроен"
    digits = "".join(c for c in card if c.isdigit())
    if len(digits) < 4:
        return "****"
    return f"**** **** **** {digits[-4:]}"

def is_admin(user_id: int) -> bool:
    # Читаем актуальный env каждый раз — важно для тестов и смены .env без рестарта
    admin = os.getenv("ADMIN_USER_ID", "") or ADMIN_USER_ID
    if not admin:
        return False
    try:
        return int(admin) == int(user_id)
    except:
        return str(admin) == str(user_id)
