"""DB queries and analytics connection for the no_water_supply flow."""

import json
import os
from datetime import datetime

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

from whatsapp_automation.db import execute_query

load_dotenv()

_TENANT_ID = os.getenv("TENT_ID", "").strip()

ANOMALY_USER_ID: int = int(os.getenv("ANOMALY_USER_ID", "21350").strip())
ANOMALY_SCHEME_ID: int = int(os.getenv("ANOMALY_SCHEME_ID", "27653").strip())

# Localised labels used to identify the "Report Issue" option in the main menu.
REPORT_ISSUE_LABEL: dict[str, str] = {
    "en": "Report Issue",
    "hi": "समस्या दर्ज करें",
}

# Localised labels used to identify the "No Water Supply" sub-option.
NO_WATER_SUPPLY_LABEL: dict[str, str] = {
    "en": "No Water Supply",
    "hi": "पानी की आपूर्ति नहीं है",
}


def get_outage_reasons(connection) -> list[dict]:
    """Return supply outage reasons from tenant config, sorted by sequenceOrder.

    Queries ``common_schema.tenant_config_master_table`` for
    ``config_key='SUPPLY_OUTAGE_REASONS'`` and returns the ``reasons`` list
    sorted by their ``sequenceOrder`` field.

    Args:
        connection: Open psycopg2 connection; caller manages lifecycle.

    Returns:
        List of reason dicts, e.g.::

            [
                {"id": "ELECTRICITY_SUPPLY_DISCONNECTED",
                 "name": "Electricity Supply Disconnected",
                 "sequenceOrder": 1, ...},
                ...
            ]

    Raises:
        RuntimeError: If no config row is found.
    """
    if not _TENANT_ID:
        raise RuntimeError("Missing TENT_ID in environment")

    query = """
        SELECT tcmt.config_value
        FROM common_schema.tenant_config_master_table AS tcmt
        WHERE config_key = %(config_key)s AND ((tenant_id = %(tenant_id)s))
    """
    rows = execute_query(
        connection,
        query,
        {"tenant_id": int(_TENANT_ID), "config_key": "SUPPLY_OUTAGE_REASONS"},
    )
    if not rows:
        raise RuntimeError(
            f"No config found for tenant_id={_TENANT_ID} and config_key='SUPPLY_OUTAGE_REASONS'"
        )

    raw = rows[0]["config_value"]
    data = json.loads(raw) if isinstance(raw, str) else raw
    reasons = data.get("reasons", [])
    return sorted(reasons, key=lambda r: r.get("sequenceOrder", 0))


def get_analytics_connection():
    """Return an open psycopg2 connection to the analytics database.

    Uses ``ANALYTICS_DB_URL``, ``ANALYTICS_DB_USERNAME``, and
    ``ANALYTICS_DB_PASSWORD`` from the environment — separate from the main
    ``DB_URL`` used by other flows so neither connection is affected by the
    other.

    The caller is responsible for closing the returned connection.

    Raises:
        ValueError: If ``ANALYTICS_DB_URL`` is missing from the environment.
    """
    load_dotenv()
    analytics_db_url = os.getenv("ANALYTICS_DB_URL", "").strip()
    analytics_db_username = os.getenv("ANALYTICS_DB_USERNAME", "").strip()
    analytics_db_password = os.getenv("ANALYTICS_DB_PASSWORD", "").strip()

    if not analytics_db_url:
        raise ValueError("Missing ANALYTICS_DB_URL in .env")

    if analytics_db_url.startswith("jdbc:"):
        analytics_db_url = analytics_db_url[len("jdbc:"):]

    return psycopg2.connect(
        analytics_db_url,
        user=analytics_db_username or None,
        password=analytics_db_password or None,
    )


def get_anomaly_rows(
    analytics_conn,
    user_id: int,
    scheme_id: int,
    sent_at: datetime,
) -> list[dict]:
    """Query anomaly_table for rows created after *sent_at*.

    ``created_at`` in ``analytics_schema.anomaly_table`` is stored as a
    timezone-aware timestamp (IST, ``+0530``).  *sent_at* must therefore also
    be an IST-aware ``datetime`` so psycopg2 produces a type-safe comparison.

    Args:
        analytics_conn: Open psycopg2 connection to the analytics DB.
        user_id:        Filter value for ``anomaly_table.user_id``.
        scheme_id:      Filter value for ``anomaly_table.scheme_id``.
        sent_at:        IST-aware datetime; only rows with ``created_at > sent_at``
                        are returned.

    Returns:
        List of dicts with at least ``type`` and ``reason`` keys.
    """
    query = """
        SELECT t.type, t.reason
        FROM analytics_schema.anomaly_table AS t
        WHERE (user_id = %(user_id)s)
          AND (scheme_id = %(scheme_id)s)
          AND (created_at > %(sent_at)s)
    """
    with analytics_conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, {"user_id": user_id, "scheme_id": scheme_id, "sent_at": sent_at})
        rows = cur.fetchall()
    return [dict(row) for row in rows]
