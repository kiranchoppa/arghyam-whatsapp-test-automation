"""DB queries specific to the select_channel flow."""

import json
import os

from dotenv import load_dotenv

from whatsapp_automation.db import execute_query

load_dotenv()

_TENANT_ID = os.getenv("TENT_ID", "").strip()

_cached_channel_config: dict | None = None


def get_user_channel(connection, contact_id: str) -> str:
    """Return the current channel_value for *contact_id* from user_channel_preference.

    The leading '+' is stripped from *contact_id* if present so callers can
    pass ``config.user_number`` directly.
    Result is NOT cached — always queries the DB so callers can verify
    post-action state.

    Args:
        connection:  Open psycopg2 connection; caller manages lifecycle.
        contact_id:  User phone number (with or without leading '+').

    Returns:
        The channel_value string (e.g. ``"BFM"``).

    Raises:
        RuntimeError: If no row is found for *contact_id*.
    """
    stripped_id = contact_id.lstrip("+")
    query = """
        SELECT ucp.channel_value
        FROM common_schema.user_channel_preference AS ucp
        WHERE contact_id = %(contact_id)s
    """
    rows = execute_query(connection, query, {"contact_id": stripped_id})
    if not rows:
        raise RuntimeError(
            f"No channel preference found for contact_id '{stripped_id}'"
        )
    return rows[0]["channel_value"]


def get_channel_config(connection) -> dict:
    """Return the parsed TENANT_SUPPORTED_CHANNELS config for the current tenant.

    Queries tenant_config_master_table for config_key='TENANT_SUPPORTED_CHANNELS'
    and returns the parsed JSON, e.g.::

        {"channels": ["IOT", "BFM", "MAN", "ELM", "PDU"]}

    Caches the result for subsequent calls within the same process.
    """
    global _cached_channel_config
    if _cached_channel_config is not None:
        return _cached_channel_config

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
        {"tenant_id": int(_TENANT_ID), "config_key": "TENANT_SUPPORTED_CHANNELS"},
    )
    if not rows:
        raise RuntimeError(
            f"No config found for tenant_id={_TENANT_ID} and config_key='TENANT_SUPPORTED_CHANNELS'"
        )

    raw = rows[0]["config_value"]
    _cached_channel_config = json.loads(raw) if isinstance(raw, str) else raw
    return _cached_channel_config
