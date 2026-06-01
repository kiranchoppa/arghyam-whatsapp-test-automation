"""Validation functions specific to the select_channel flow.

Every validation function returns a ``(passed: bool, message: str)`` tuple.
- On success : ``(True, "")``
- On failure : ``(False, "<reason>")``
"""

from whatsapp_automation.services.select_channel_service import get_user_channel


def validate_channel_selection_prompt(
    response: str,
    channel_selection: dict,
    channels: list[str],
    lang_symbol: str,
) -> tuple[bool, str]:
    """Check that *response* contains the CHANNEL_SELECTION prompt and all channel options.

    Args:
        response:          Raw text received from WhatsApp after sending the
                           "select channel" option number.
        channel_selection: The ``CHANNEL_SELECTION`` screen block from the
                           tenant config (``config["screens"]["CHANNEL_SELECTION"]``).
        channels:          List of channel names from ``get_channel_config``,
                           e.g. ``["IOT", "BFM", "MAN", "ELM", "PDU"]``.
        lang_symbol:       ISO language symbol resolved for the user (e.g. ``"en"``).

    Returns:
        ``(True, "")`` if all checks pass, otherwise
        ``(False, "<reason>")`` describing the first failed check.
    """
    prompt = channel_selection["prompt"][lang_symbol]
    if prompt not in response:
        return False, (
            f"Channel selection prompt not found in response.\n"
            f"  Expected : {prompt!r}\n"
            f"  Response : {response!r}"
        )

    for channel in channels:
        if channel not in response:
            return False, (
                f"Channel option not found in response.\n"
                f"  Expected channel : {channel!r}\n"
                f"  Response         : {response!r}"
            )

    return True, ""


def validate_channel_selection_success(
    response: str,
    channel_selection: dict,
    lang_symbol: str,
    connection,
    contact_id: str,
    expected_channel: str,
) -> tuple[bool, str]:
    """Check the WhatsApp success reply and verify the DB channel preference is updated.

    Two checks are performed in order:
    1. WhatsApp reply contains the expected success message text (from tenant
       config).  If the config has no success_message key the text check is
       skipped and only the DB check runs.
    2. ``user_channel_preference.channel_value`` for *contact_id* equals
       *expected_channel*, confirming the server actually updated the record.

    Args:
        response:          Raw text received from WhatsApp after the "Yes" confirmation.
        channel_selection: The ``CHANNEL_SELECTION`` screen block from the
                           tenant config (``config["screens"]["CHANNEL_SELECTION"]``).
        lang_symbol:       ISO language symbol resolved for the user (e.g. ``"en"``).
        connection:        Open psycopg2 connection; caller manages lifecycle.
        contact_id:        User phone number passed to ``get_user_channel``
                           (with or without leading '+').
        expected_channel:  The channel name the user just selected (e.g. ``"BFM"``).

    Returns:
        ``(True, "")`` if all checks pass, otherwise
        ``(False, "<reason>")`` describing the first failed check.
    """
    if not response:
        return False, "No success reply received from WhatsApp after confirmation."

    success_text_by_lang = channel_selection.get("success_message") or {}
    success_message = success_text_by_lang.get(lang_symbol)

    if success_message is not None and success_message not in response:
        return False, (
            f"Channel selection success message not found in response.\n"
            f"  Expected : {success_message!r}\n"
            f"  Response : {response!r}"
        )

    try:
        actual_channel = get_user_channel(connection, contact_id)
    except Exception as exc:
        return False, f"DB check failed while reading user channel preference: {exc}"

    if actual_channel != expected_channel:
        return False, (
            f"DB channel preference not updated correctly.\n"
            f"  Expected : {expected_channel!r}\n"
            f"  Actual   : {actual_channel!r}"
        )

    return True, ""
