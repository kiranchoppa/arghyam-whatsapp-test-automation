"""Configuration loading and validation."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_SEND_TIMEOUT = 120
DEFAULT_RESPONSE_TIMEOUT = 60


@dataclass(frozen=True)
class WhatsAppConfig:
    recipient_number: str
    message: str
    browser: str
    edge_profile_dir: str
    edge_profile_name: str
    keep_browser_open: bool
    send_timeout: int
    response_timeout: int
    db_url: str
    db_username: str
    db_password: str
    common_schema: str
    tent_config: str
    tent_id: int


def validate_phone(number, variable_name):
    if not number.startswith("+"):
        raise ValueError(f"{variable_name} must start with '+' and country code.")
    if not number[1:].isdigit():
        raise ValueError(f"{variable_name} must contain only digits after '+'.")
    return number


def load_config():
    load_dotenv()
    recipient_number = os.getenv("JALSHOOCHAK_WHATSAPP_NUMBER", "").strip()
    message = os.getenv("WHATSAPP_MESSAGE", "Pump reading test message.").strip()
    browser = os.getenv("WHATSAPP_BROWSER", "edge").strip().lower()
    edge_profile_dir = os.path.expanduser(
        os.getenv("EDGE_PROFILE_DIR", "~/.config/microsoft-edge").strip()
    )
    edge_profile_name = os.getenv("EDGE_PROFILE_NAME", "Default").strip()
    keep_browser_open = (
        os.getenv("KEEP_BROWSER_OPEN", "false").strip().lower() == "true"
    )
    send_timeout = int(
        os.getenv("SEND_TIMEOUT_SECONDS", str(DEFAULT_SEND_TIMEOUT)).strip()
    )
    response_timeout = int(
        os.getenv("RESPONSE_TIMEOUT_SECONDS", str(DEFAULT_RESPONSE_TIMEOUT)).strip()
    )

    db_url = os.getenv("DB_URL", "").strip()
    db_username = os.getenv("DB_USERNAME", "").strip()
    db_password = os.getenv("DB_PASSWORD", "").strip()
    common_schema = os.getenv("COMMON_SCHEMA", "common_schema").strip()
    tent_config = os.getenv("TENT_CONFIG", "tenant_config_master_table").strip()
    tent_id = int(os.getenv("TENT_ID", "17").strip())

    if not recipient_number:
        raise ValueError("Missing JALSHOOCHAK_WHATSAPP_NUMBER in .env")
    if not message:
        raise ValueError("WHATSAPP_MESSAGE is empty in .env")
    if browser not in ("edge", "chromium"):
        raise ValueError("WHATSAPP_BROWSER must be 'edge' or 'chromium'")
    if send_timeout < 10:
        raise ValueError("SEND_TIMEOUT_SECONDS should be at least 10")
    if response_timeout < 5:
        raise ValueError("RESPONSE_TIMEOUT_SECONDS should be at least 5")
    if not db_url:
        raise ValueError("Missing DB_URL in .env")
    if not db_username:
        raise ValueError("Missing DB_USERNAME in .env")
    if not db_password:
        raise ValueError("Missing DB_PASSWORD in .env")

    validate_phone(recipient_number, "JALSHOOCHAK_WHATSAPP_NUMBER")

    return WhatsAppConfig(
        recipient_number=recipient_number,
        message=message,
        browser=browser,
        edge_profile_dir=edge_profile_dir,
        edge_profile_name=edge_profile_name,
        keep_browser_open=keep_browser_open,
        send_timeout=send_timeout,
        response_timeout=response_timeout,
        db_url=db_url,
        db_username=db_username,
        db_password=db_password,
        common_schema=common_schema,
        tent_config=tent_config,
        tent_id=tent_id,
    )
