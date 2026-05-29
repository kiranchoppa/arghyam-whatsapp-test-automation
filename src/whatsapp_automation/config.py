"""Configuration loading and validation."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_SEND_TIMEOUT = 120
DEFAULT_RESPONSE_TIMEOUT = 60


@dataclass(frozen=True)
class WhatsAppConfig:
    recipient_number: str
    user_number: str
    start_message: str
    browser: str
    edge_profile_dir: str
    edge_profile_name: str
    keep_browser_open: bool
    send_timeout: int
    response_timeout: int


def validate_phone(number, variable_name):
    if not number.startswith("+"):
        raise ValueError(f"{variable_name} must start with '+' and country code.")
    if not number[1:].isdigit():
        raise ValueError(f"{variable_name} must contain only digits after '+'.")
    return number


def load_config():
    load_dotenv()
    recipient_number = os.getenv("JALSHOOCHAK_WHATSAPP_NUMBER", "").strip()
    user_number = os.getenv("USER_NUMBER", "").strip()
    app_env = os.getenv("APP_ENV", "dev").strip().lower()
    start_message = os.getenv("START_MESSAGE", "").strip()
    if not start_message:
        start_message = "startstaging" if app_env == "staging" else "start"
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

    if not recipient_number:
        raise ValueError("Missing JALSHOOCHAK_WHATSAPP_NUMBER in .env")
    if not user_number:
        raise ValueError("Missing USER_NUMBER in .env")
    if app_env not in ("dev", "staging"):
        raise ValueError("APP_ENV must be 'dev' or 'staging'")
    if not start_message:
        raise ValueError("START_MESSAGE must not be empty")
    if browser not in ("edge", "chromium"):
        raise ValueError("WHATSAPP_BROWSER must be 'edge' or 'chromium'")
    if send_timeout < 10:
        raise ValueError("SEND_TIMEOUT_SECONDS should be at least 10")
    if response_timeout < 5:
        raise ValueError("RESPONSE_TIMEOUT_SECONDS should be at least 5")

    validate_phone(recipient_number, "JALSHOOCHAK_WHATSAPP_NUMBER")
    validate_phone(user_number, "USER_NUMBER")

    return WhatsAppConfig(
        recipient_number=recipient_number,
        user_number=user_number,
        start_message=start_message,
        browser=browser,
        edge_profile_dir=edge_profile_dir,
        edge_profile_name=edge_profile_name,
        keep_browser_open=keep_browser_open,
        send_timeout=send_timeout,
        response_timeout=response_timeout,
    )
