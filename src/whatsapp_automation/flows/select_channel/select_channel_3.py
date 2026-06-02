"""select_channel flow — test scenario 3 (cancel confirmation).

Steps
-----
1.  Bootstrap: send start message, validate main menu (DB + WhatsApp).
2.  DB: read current preferred channel, fetch channel config and tenant config.
    Pick the first channel from the config list that is not the current preference.
3.  Identify the option number associated with "Select Channel".
4.  Send that number and receive the channel selection prompt.
5.  Validate the channel selection prompt and available channels.
6.  Identify the number for the alternate channel from the channel list.
7.  Send that number and receive the "Are you sure?" confirmation prompt.
8.  Send "No" to cancel — bot returns to the main menu without updating DB.
9.  Validate the main menu reply and verify the preferred channel is unchanged.
"""

import re

from whatsapp_automation.db import get_connection
from whatsapp_automation.flows.bootstrap import bootstrap_flow
from whatsapp_automation.messaging import send_message, wait_for_nth_reply
from whatsapp_automation.services.common_service import (
    SELECT_CHANNEL_LABEL,
    get_tenant_config,
)
from whatsapp_automation.services.select_channel_service import (
    get_channel_config,
    get_user_channel,
)
from whatsapp_automation.validations.common_validations import validate_main_menu
from whatsapp_automation.validations.select_channel_validations import (
    validate_channel_preference,
    validate_channel_selection_prompt,
)

def _find_option_number(options: dict, lang_symbol: str) -> str | None:
    """Return the option number whose label matches the "Select Channel" label for *lang_symbol*.

    Performs a case-insensitive substring match against the localised label so
    minor punctuation or spacing differences in the config do not cause misses.

    Args:
        options:     The ``options`` dict from the ITEM_SELECTION screen,
                     keyed by option number strings (e.g. ``{"1": {...}, "2": {...}}``).
        lang_symbol: The ISO language symbol resolved for the user (e.g. ``"en"`` or ``"hi"``).

    Returns:
        The matching option number string (e.g. ``"2"``), or ``None`` if not found.
    """
    keyword = SELECT_CHANNEL_LABEL.get(lang_symbol, SELECT_CHANNEL_LABEL["en"])
    for key, option in options.items():
        label = option.get("label", {}).get(lang_symbol, "")
        if keyword.lower() in label.lower():
            match = re.search(r"\d+$", key)
            return match.group() if match else key
    return None


def run(driver, config, menu_context: dict | None = None) -> tuple[bool, str]:
    """Test scenario 3 for the select_channel flow — cancel with "No".

    Returns:
        ``(True, "")`` on full pass, ``(False, reason)`` on any failure.
    """
    # ------------------------------------------------------------------
    # Step 1: Bootstrap — send start message + validate main menu
    # ------------------------------------------------------------------
    ok, err, main_menu = bootstrap_flow(driver, config, menu_context)
    if not ok:
        return False, f"[select_channel_3] Bootstrap failed: {err}"

    lang_symbol = main_menu["lang_symbol"]

    # ------------------------------------------------------------------
    # Step 2: DB — preferred channel, channel config, tenant config
    # ------------------------------------------------------------------
    original_channel = None
    channel_config = None
    tenant_config = None

    try:
        connection = get_connection()
        try:
            original_channel = get_user_channel(connection, config.user_number)
            channel_config = get_channel_config(connection)
            tenant_config = get_tenant_config(connection)
        finally:
            connection.close()
    except Exception as exc:
        return False, f"[select_channel_3] DB/service error: {exc}"

    channels = channel_config.get("channels", [])
    channel_selection = tenant_config["screens"]["CHANNEL_SELECTION"]

    target_channel = next((ch for ch in channels if ch != original_channel), None)
    if target_channel is None:
        return False, "[select_channel_3] No alternate channel found in channel list to test cancel flow."
    print(
        f"[select_channel_3] Current preferred channel: {original_channel!r} "
        f"→ will select {target_channel!r} then cancel"
    )

    # ------------------------------------------------------------------
    # Step 3: Identify "Select Channel" option number (language-aware)
    # ------------------------------------------------------------------
    select_channel_number = _find_option_number(
        main_menu["item_selection"]["options"], lang_symbol
    )
    if select_channel_number is None:
        return False, "[select_channel_3] Could not find 'Select Channel' option in main menu."
    print(f"[select_channel_3] 'Select Channel' option number: {select_channel_number}")

    # ------------------------------------------------------------------
    # Step 4: Send the "Select Channel" option number and receive reply
    # ------------------------------------------------------------------
    try:
        channel_reply = send_message(driver, select_channel_number, config.response_timeout)
        print(f"[select_channel_3] Channel selection reply: {channel_reply}")
    except Exception as exc:
        return False, f"[select_channel_3] Error sending 'Select Channel' option: {exc}"

    # ------------------------------------------------------------------
    # Step 5: Validate channel selection prompt and available channels
    # ------------------------------------------------------------------
    passed, message = validate_channel_selection_prompt(
        channel_reply, channel_selection, channels, lang_symbol
    )
    if not passed:
        return False, f"[select_channel_3] Channel selection prompt validation failed: {message}"
    print("[select_channel_3] Channel selection prompt validation: PASSED")

    # ------------------------------------------------------------------
    # Step 6: Identify the alternate channel's position in the list (1-based)
    # ------------------------------------------------------------------
    if target_channel not in channels:
        return (
            False,
            f"[select_channel_3] '{target_channel}' not found in channel list: {channels}",
        )
    channel_number = str(channels.index(target_channel) + 1)
    print(f"[select_channel_3] '{target_channel}' option number: {channel_number}")

    # ------------------------------------------------------------------
    # Step 7: Send channel number — bot replies with "Are you sure?" prompt.
    # ------------------------------------------------------------------
    try:
        are_you_sure_reply = send_message(driver, channel_number, config.response_timeout)
        print(f"[select_channel_3] 'Are you sure?' prompt: {are_you_sure_reply}")
    except Exception as exc:
        return False, f"[select_channel_3] Error sending channel option: {exc}"

    # ------------------------------------------------------------------
    # Step 8: Send "No" to cancel.  The bot does not prompt again; it returns
    # directly to the main menu without updating the DB preference.
    # ------------------------------------------------------------------
    try:
        cancel_reply = send_message(driver, "No", config.response_timeout)
        print(f"[select_channel_3] After 'No' reply: {cancel_reply}")
    except Exception as exc:
        return False, f"[select_channel_3] Error sending 'No' confirmation: {exc}"

    if not cancel_reply:
        cancel_reply = wait_for_nth_reply(driver, 1, config.response_timeout)
        print(f"[select_channel_3] Main menu after 'No' (waited): {cancel_reply}")

    # ------------------------------------------------------------------
    # Step 9: Validate main menu and verify DB channel preference unchanged
    # ------------------------------------------------------------------
    passed, message = validate_main_menu(cancel_reply, main_menu)
    if not passed:
        return False, f"[select_channel_3] Main menu validation after cancel failed: {message}"
    print("[select_channel_3] Main menu validation after cancel: PASSED")

    try:
        connection = get_connection()
        try:
            passed, message = validate_channel_preference(
                connection,
                config.user_number,
                original_channel,
            )
        finally:
            connection.close()
    except Exception as exc:
        return False, f"[select_channel_3] DB error during channel preference validation: {exc}"

    if not passed:
        return (
            False,
            f"[select_channel_3] Channel preference validation failed: {message}",
        )

    print("[select_channel_3] Channel preference validation: PASSED")
    return True, ""
