"""DB queries specific to the select_language flow."""

from whatsapp_automation.db import execute_query

_cached_language_list: list[str] | None = None


def get_language_list(connection) -> list[str]:
    """Return the list of active language names from language_master_table.

    Queries ``tenant_as.language_master_table`` for rows where ``status = 1``
    and returns a flat list of language name strings, e.g.
    ``["English", "Hindi", "Marathi"]``.

    Caches the result for subsequent calls within the same process.

    Args:
        connection: Open psycopg2 connection; caller manages lifecycle.

    Returns:
        List of language name strings ordered by DB default.

    Raises:
        RuntimeError: If no active languages are found.
    """
    global _cached_language_list
    if _cached_language_list is not None:
        return _cached_language_list

    query = """
        SELECT lmt.language_name
        FROM tenant_as.language_master_table AS lmt
        WHERE status = 1
    """
    rows = execute_query(connection, query)
    if not rows:
        raise RuntimeError("No active languages found in language_master_table.")

    _cached_language_list = [row["language_name"] for row in rows]
    return _cached_language_list


def get_user_language_preference(connection, contact_id: str) -> str:
    """Return the current language_value for *contact_id* from user_language_preference.

    The leading '+' is stripped from *contact_id* if present so callers can
    pass ``config.user_number`` directly.
    Result is NOT cached — always queries the DB so callers can verify
    post-action state.

    Args:
        connection:  Open psycopg2 connection; caller manages lifecycle.
        contact_id:  User phone number (with or without leading '+').

    Returns:
        The language_value string (e.g. ``"English"`` or ``"Hindi"``).

    Raises:
        RuntimeError: If no row is found for *contact_id*.
    """
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
    return rows[0]["language_value"]
