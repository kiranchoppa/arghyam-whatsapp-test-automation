"""Glific message-template service.

Responsibilities:
- Fetch the GLIFIC_MESSAGE_TEMPLATES config value from the database.
- Parse and extract ITEM_SELECTION options from the config JSON.
- Validate a WhatsApp bot response against those options.

Database access is delegated to db.py (connection + execution).
SQL strings are sourced from queries.py.
"""

import json
import sys

from whatsapp_automation.db import execute_query, get_connection
from whatsapp_automation.queries import GET_TENANT_CONFIG_VALUE

_CONFIG_KEY = "GLIFIC_MESSAGE_TEMPLATES"


# ---------------------------------------------------------------------------
# Data-fetching helpers
# ---------------------------------------------------------------------------

def fetch_glific_templates(config):
    """Fetch and return the parsed GLIFIC_MESSAGE_TEMPLATES config_value from the DB.

    Uses the DB connection details and table coordinates stored in config.
    Raises RuntimeError if the expected row is absent.
    """
    query = GET_TENANT_CONFIG_VALUE.format(
        schema=config.common_schema,
        table=config.tent_config,
    )

    conn = get_connection(config.db_url, config.db_username, config.db_password)
    try:
        rows = execute_query(
            conn,
            query,
            {"tenant_id": config.tent_id, "config_key": _CONFIG_KEY},
        )
    finally:
        conn.close()

    if not rows:
        raise RuntimeError(
            f"No row found in {config.common_schema}.{config.tent_config} for "
            f"tenant_id={config.tent_id} and config_key='{_CONFIG_KEY}'"
        )

    raw_value = rows[0]["config_value"]
    if isinstance(raw_value, str):
        # raw_decode parses the first valid JSON object and ignores any
        # trailing characters (whitespace, extra data) that follow it.
        parsed, _ = json.JSONDecoder().raw_decode(raw_value.strip())
        return parsed
    return dict(raw_value)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def extract_item_selection_options(config_value):
    """Return English labels of all ITEM_SELECTION options, sorted by order."""
    screens = config_value.get("screens", {})
    item_selection = screens.get("ITEM_SELECTION", {})
    options = item_selection.get("options") or {}

    sorted_options = sorted(options.values(), key=lambda o: o.get("order", 0))
    return [
        opt["label"]["en"]
        for opt in sorted_options
        if opt.get("label", {}).get("en")
    ]


# ---------------------------------------------------------------------------
# Validation / comparison
# ---------------------------------------------------------------------------

def validate_item_selection(response_message, config):
    """Fetch ITEM_SELECTION options from the DB and compare with response_message.

    Prints a [PASS] line if any expected option label is found in the response,
    or a [FAIL] line with the full response if none match.
    """
    print("\n--- Validating bot response against DB config ---")

    try:
        config_value = fetch_glific_templates(config)
    except Exception as exc:  # noqa: BLE001
        print(f"[DB ERROR] Could not fetch templates: {exc}", file=sys.stderr)
        return

    expected_options = extract_item_selection_options(config_value)
    print(f"Expected ITEM_SELECTION options: {expected_options}")

    matched = [opt for opt in expected_options if opt in response_message]
    if matched:
        print(f"[PASS] Bot response contains expected option(s): {matched}")
    else:
        print(
            "[FAIL] Bot response does not contain any expected ITEM_SELECTION option.\n"
            f"       Response: {response_message!r}"
        )
