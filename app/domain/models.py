from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

@dataclass
class Campaign:
    id: Optional[int] = None
    owner_id: int = 0
    platform: str = "telegram"
    campaign_type: str = "own_channel_post"
    country: str = ""
    city: str = ""
    audience_source: str = "bot_subscribers"
    audience_mode: str = "subscribers"
    requested_limit: int = 0
    message_text: str = ""
    link: str = ""
    schedule_at: Optional[str] = None
    status: str = "draft"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    idempotency_key: Optional[str] = None
    recipients_json: str = "[]"

@dataclass
class Contact:
    id: Optional[int] = None
    owner_id: int = 0
    provider: str = "telegram"
    external_id: str = ""
    consent_status: str = "granted"  # granted, revoked, pending
    consent_source: str = ""
    consent_at: Optional[str] = None
    unsubscribed_at: Optional[str] = None
    display_name: str = ""

@dataclass
class Delivery:
    id: Optional[int] = None
    campaign_id: int = 0
    recipient: str = ""
    status: str = "pending"  # pending, queued, sending, sent, delivered, failed, skipped, retry, cancelled
    attempts: int = 0
    provider_message_id: Optional[str] = None
    error_code: Optional[str] = None
    error_text: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    next_retry_at: Optional[str] = None

@dataclass
class ActivityEvent:
    id: Optional[int] = None
    owner_id: int = 0
    campaign_id: Optional[int] = None
    event: str = ""
    details: str = ""
    created_at: Optional[str] = None

@dataclass
class Setting:
    owner_id: int = 0
    default_country: str = ""
    timezone: str = "Europe/Kiev"
    test_mode: int = 1
    notifications: int = 1
    queue_limit: int = 100
    language: str = "ru"

@dataclass
class ProviderConnection:
    id: Optional[int] = None
    owner_id: int = 0
    provider: str = ""
    status: str = "not_connected"  # not_connected, connected, configuration_error, permission_error, service_error
    meta: str = ""
    updated_at: Optional[str] = None

@dataclass
class User:
    user_id: int = 0
    username: str = ""
    first_name: str = ""
    created_at: Optional[str] = None
    free_used: int = 0
    free_total: int = 10
    subscription_status: str = "free"  # free, active, expired
    subscription_expires_at: Optional[str] = None
    updated_at: Optional[str] = None
    language: str = "ru"

@dataclass
class PaymentRequest:
    id: Optional[int] = None
    user_id: int = 0
    created_at: Optional[str] = None
    status: str = "pending"  # pending, approved, rejected
    amount_usd: float = 1.0
    period_days: int = 30
    payment_mode: str = "manual_placeholder"
    card_last4: str = ""
    admin_id: Optional[int] = None
    reviewed_at: Optional[str] = None
    details: str = ""
