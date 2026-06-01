"""Common DB service functions shared across all flows."""

import json
import os

from dotenv import load_dotenv

from whatsapp_automation.db import execute_query
from whatsapp_automation.language_map import get_language_symbol

load_dotenv()

_TENANT_ID = os.getenv("TENT_ID", "").strip()

_cached_language: str | None = None
_cached_config_value: dict | None = None


def get_user_language(connection, contact_id: str) -> str:
    """Return the language name for *contact_id* from user_language_preference.

    The leading '+' is stripped from *contact_id* if present so callers can
    pass ``config.recipient_number`` directly.
    Caches the result for subsequent calls within the same process.
    """
    global _cached_language
    if _cached_language is not None:
        return _cached_language

    stripped_id = contact_id.lstrip("+")
    query = """
        SELECT ulp.language_value
        FROM common_schema.user_language_preference AS ulp
        WHERE contact_id = %(contact_id)s
    """
    rows = execute_query(connection, query, {"contact_id": stripped_id})
    if not rows:
        raise RuntimeError(
            f"No language preference found for contact_id '{stripped_id}'"
        )
    _cached_language = rows[0]["language_value"]
    return _cached_language


def get_tenant_config(connection) -> dict:
    """Return the parsed GLIFIC_MESSAGE_TEMPLATES config blob from tenant_config_master_table.

    Uses ``_TENANT_ID`` from the environment.
    Caches the result for subsequent calls within the same process.
    """
    global _cached_config_value
    if _cached_config_value is not None:
        return _cached_config_value

    if not _TENANT_ID:
        raise RuntimeError("Missing TENT_ID in environment")

    query = """
        SELECT tcmt.config_value
        FROM common_schema.tenant_config_master_table AS tcmt
        WHERE (tenant_id = %(tenant_id)s) AND (config_key = %(config_key)s)
    """
    rows = execute_query(
        connection,
        query,
        {"tenant_id": int(_TENANT_ID), "config_key": "GLIFIC_MESSAGE_TEMPLATES"},
    )
    if not rows:
        raise RuntimeError(
            f"No config found for tenant_id={_TENANT_ID} and config_key='GLIFIC_MESSAGE_TEMPLATES'"
        )

    raw = rows[0]["config_value"]
    _cached_config_value = json.loads(raw) if isinstance(raw, str) else raw
    return _cached_config_value


def get_main_menu(connection, contact_id: str) -> dict:
    """Return the ITEM_SELECTION screen data and resolved language symbol for *contact_id*.

    Steps:
    1. Fetch the user's language (e.g. 'English') from the DB.
    2. Map it to an ISO symbol (e.g. 'en') via language_map.
    3. Fetch the tenant config JSON from the DB.
    4. Return the raw ITEM_SELECTION block alongside the language symbol so
       callers can format or validate as needed.

    Returns a dict of the form::

        {
            "item_selection": { ...ITEM_SELECTION block from config... },
            "lang_symbol": "en",
        }
    """
    language_name = get_user_language(connection, contact_id)
    lang_symbol = get_language_symbol(language_name)

    config = get_tenant_config(connection)
    item_selection = config["screens"]["ITEM_SELECTION"]

    return {"item_selection": item_selection, "lang_symbol": lang_symbol}
