"""Validation functions for the no_water_supply flow.

Every validation function returns a ``(passed: bool, message: str)`` tuple.
- On success : ``(True, "")``
- On failure : ``(False, "<reason>")``
"""

from datetime import datetime

from whatsapp_automation.services.no_water_supply_service import get_anomaly_rows


def validate_outage_reasons_prompt(
    response: str,
    reasons: list[dict],
) -> tuple[bool, str]:
    """Check that *response* contains all expected outage reason names.

    Args:
        response: Raw text received from WhatsApp after sending the
                  "No Water Supply" option number.
        reasons:  Sorted list of reason dicts from ``get_outage_reasons``,
                  each containing at least a ``"name"`` key.

    Returns:
        ``(True, "")`` if all reason names are present, otherwise
        ``(False, "<reason>")`` describing the first missing entry.
    """
    for reason in reasons:
        name = reason.get("name", "")
        if not name:
            continue
        if name not in response:
            return False, (
                f"Outage reason not found in response.\n"
                f"  Expected : {name!r}\n"
                f"  Response : {response!r}"
            )
    return True, ""


def validate_anomaly_record(
    analytics_conn,
    user_id: int,
    scheme_id: int,
    sent_at: datetime,
) -> tuple[bool, str]:
    """Assert that at least one anomaly row was created after *sent_at*.

    ``created_at`` in ``analytics_schema.anomaly_table`` is stored as a
    timezone-aware IST timestamp (``+0530``).  *sent_at* must be IST-aware
    so the psycopg2 ``>`` comparison is type-safe.

    Args:
        analytics_conn: Open psycopg2 connection to the analytics database.
        user_id:        ``anomaly_table.user_id`` filter value.
        scheme_id:      ``anomaly_table.scheme_id`` filter value.
        sent_at:        IST-aware datetime captured just before sending the
                        reason option.

    Returns:
        ``(True, "")`` if a matching row exists with non-empty ``type`` or
        ``reason``, otherwise ``(False, "<reason>")``.
    """
    try:
        rows = get_anomaly_rows(analytics_conn, user_id, scheme_id, sent_at)
    except Exception as exc:
        return False, f"Analytics DB query failed: {exc}"

    if not rows:
        return False, (
            f"No anomaly row found in analytics_schema.anomaly_table "
            f"for user_id={user_id}, scheme_id={scheme_id} "
            f"with created_at > {sent_at.isoformat()}"
        )

    row = rows[-1]
    if not row.get("type") and not row.get("reason"):
        return False, (
            f"Anomaly row found but both 'type' and 'reason' are empty.\n"
            f"  Row: {row}"
        )

    print(
        f"[no_water_supply] Anomaly row — type: {row.get('type')!r}, "
        f"reason: {row.get('reason')!r}"
    )
    return True, ""


def validate_no_anomaly_record(
    analytics_conn,
    user_id: int,
    scheme_id: int,
    sent_at: datetime,
) -> tuple[bool, str]:
    """Assert that NO anomaly row was created after *sent_at*.

    Used when a submission is expected to be rejected (e.g. invalid input)
    and the DB should remain unchanged.

    Args:
        analytics_conn: Open psycopg2 connection to the analytics database.
        user_id:        ``anomaly_table.user_id`` filter value.
        scheme_id:      ``anomaly_table.scheme_id`` filter value.
        sent_at:        IST-aware datetime; checks that no row has
                        ``created_at > sent_at``.

    Returns:
        ``(True, "")`` if no matching row exists, otherwise
        ``(False, "<reason>")`` listing the unexpected rows.
    """
    try:
        rows = get_anomaly_rows(analytics_conn, user_id, scheme_id, sent_at)
    except Exception as exc:
        return False, f"Analytics DB query failed: {exc}"

    if rows:
        return False, (
            f"Expected no anomaly rows after {sent_at.isoformat()} but found {len(rows)}:\n"
            + "\n".join(f"  {r}" for r in rows)
        )

    return True, ""


def validate_anomaly_others_record(
    analytics_conn,
    user_id: int,
    scheme_id: int,
    sent_at: datetime,
    expected_type: str,
    expected_reason: str,
) -> tuple[bool, str]:
    """Assert that an anomaly row created after *sent_at* has the expected type and reason.

    Used by the ``no_water_supply_2`` (Others) flow to confirm:
    - ``type`` equals *expected_type* (e.g. ``"NO_SUBMISSION"``)
    - ``reason`` equals the custom message sent by the user

    Args:
        analytics_conn:  Open psycopg2 connection to the analytics database.
        user_id:         ``anomaly_table.user_id`` filter value.
        scheme_id:       ``anomaly_table.scheme_id`` filter value.
        sent_at:         IST-aware datetime captured just before sending the
                         custom reason message.
        expected_type:   The exact ``type`` value expected in the DB row.
        expected_reason: The exact custom message sent; must match ``reason``
                         in the DB row.

    Returns:
        ``(True, "")`` if all checks pass, otherwise ``(False, "<reason>")``.
    """
    try:
        rows = get_anomaly_rows(analytics_conn, user_id, scheme_id, sent_at)
    except Exception as exc:
        return False, f"Analytics DB query failed: {exc}"

    if not rows:
        return False, (
            f"No anomaly row found in analytics_schema.anomaly_table "
            f"for user_id={user_id}, scheme_id={scheme_id} "
            f"with created_at > {sent_at.isoformat()}"
        )

    row = rows[-1]
    actual_type = row.get("type", "")
    actual_reason = row.get("reason", "")

    print(
        f"[no_water_supply_2] Anomaly row — type: {actual_type!r}, "
        f"reason: {actual_reason!r}"
    )

    if actual_type != expected_type:
        return False, (
            f"Anomaly row 'type' mismatch.\n"
            f"  Expected : {expected_type!r}\n"
            f"  Actual   : {actual_type!r}"
        )

    if actual_reason != expected_reason:
        return False, (
            f"Anomaly row 'reason' mismatch.\n"
            f"  Expected : {expected_reason!r}\n"
            f"  Actual   : {actual_reason!r}"
        )

    return True, ""
