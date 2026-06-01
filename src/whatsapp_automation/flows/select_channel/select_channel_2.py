"""select_channel flow — test scenario 2.

Steps
-----
1.  Bootstrap: send start message, validate main menu (DB + WhatsApp).
2.  DB: fetch channel config and tenant config.
3.  Identify the option number associated with "Select Channel".
4.  Send that number and receive the channel selection prompt.
5.  Validate the channel selection prompt and available channels.
6.  Identify the number associated with "IOT" from the channel list.
7.  Send IOT number and receive the "Are you sure?" confirmation prompt.
8.  Send "Yes" to confirm and receive the final success reply.
9.  Validate the channel selection success message and verify DB channel preference.
"""

import re

from whatsapp_automation.db import get_connection
from whatsapp_automation.flows.bootstrap import bootstrap_flow
from whatsapp_automation.messaging import send_message, wait_for_nth_reply
from whatsapp_automation.services.common_service import get_tenant_config
from whatsapp_automation.services.select_channel_service import get_channel_config
from whatsapp_automation.validations.select_channel_validations import (
    validate_channel_selection_prompt,
    validate_channel_selection_success,
)

_TARGET_CHANNEL = "IOT"

# Localised labels used to identify the "Select Channel" option in the main menu.
# Keys are ISO language symbols as returned by language_map.get_language_symbol().
_SELECT_CHANNEL_LABEL: dict[str, str] = {
    "en": "Select Channel",
    "hi": "चैनल चुनें",
}


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
    keyword = _SELECT_CHANNEL_LABEL.get(lang_symbol, _SELECT_CHANNEL_LABEL["en"])
    for key, option in options.items():
        label = option.get("label", {}).get(lang_symbol, "")
        if keyword.lower() in label.lower():
            match = re.search(r"\d+$", key)
            return match.group() if match else key
    return None


def run(driver, config) -> tuple[bool, str]:
    """Test scenario 2 for the select_channel flow.

    Returns:
        ``(True, "")`` on full pass, ``(False, reason)`` on any failure.
    """
    # ------------------------------------------------------------------
    # Step 1: Bootstrap — send start message + validate main menu
    # ------------------------------------------------------------------
    ok, err, main_menu = bootstrap_flow(driver, config)
    if not ok:
        return False, f"[select_channel_2] Bootstrap failed: {err}"

    lang_symbol = main_menu["lang_symbol"]

    # ------------------------------------------------------------------
    # Step 2: DB — fetch channel config and tenant config
    # ------------------------------------------------------------------
    channel_config = None
    tenant_config = None

    try:
        connection = get_connection()
        try:
            channel_config = get_channel_config(connection)
            tenant_config = get_tenant_config(connection)
        finally:
            connection.close()
    except Exception as exc:
        return False, f"[select_channel_2] DB/service error: {exc}"

    channels = channel_config.get("channels", [])
    channel_selection = tenant_config["screens"]["CHANNEL_SELECTION"]

    # ------------------------------------------------------------------
    # Step 3: Identify "Select Channel" option number (language-aware)
    # ------------------------------------------------------------------
    select_channel_number = _find_option_number(
        main_menu["item_selection"]["options"], lang_symbol
    )
    if select_channel_number is None:
        return False, "[select_channel_2] Could not find 'Select Channel' option in main menu."
    print(f"[select_channel_2] 'Select Channel' option number: {select_channel_number}")

    # ------------------------------------------------------------------
    # Step 4: Send the "Select Channel" option number and receive reply
    # ------------------------------------------------------------------
    try:
        channel_reply = send_message(driver, select_channel_number, config.response_timeout)
        print(f"[select_channel_2] Channel selection reply: {channel_reply}")
    except Exception as exc:
        return False, f"[select_channel_2] Error sending 'Select Channel' option: {exc}"

    # ------------------------------------------------------------------
    # Step 5: Validate channel selection prompt and available channels
    # ------------------------------------------------------------------
    passed, message = validate_channel_selection_prompt(
        channel_reply, channel_selection, channels, lang_symbol
    )
    if not passed:
        return False, f"[select_channel_2] Channel selection prompt validation failed: {message}"
    print("[select_channel_2] Channel selection prompt validation: PASSED")

    # ------------------------------------------------------------------
    # Step 6: Identify IOT number from channel list (1-based index)
    # ------------------------------------------------------------------
    if _TARGET_CHANNEL not in channels:
        return False, f"[select_channel_2] '{_TARGET_CHANNEL}' not found in channel list: {channels}"
    iot_number = str(channels.index(_TARGET_CHANNEL) + 1)
    print(f"[select_channel_2] '{_TARGET_CHANNEL}' option number: {iot_number}")

    # ------------------------------------------------------------------
    # Step 7: Send IOT number — bot replies with "Are you sure?" prompt.
    # The reply is a WhatsApp interactive-button message rendered as:
    #   "Are you sure?\n<timestamp>\nYes\nNo"
    # ------------------------------------------------------------------
    try:
        are_you_sure_reply = send_message(driver, iot_number, config.response_timeout)
        print(f"[select_channel_2] 'Are you sure?' prompt: {are_you_sure_reply}")
    except Exception as exc:
        return False, f"[select_channel_2] Error sending IOT option: {exc}"

    # ------------------------------------------------------------------
    # Step 8: Send "Yes" to confirm and receive the final success reply.
    # ------------------------------------------------------------------
    try:
        confirmation_reply = send_message(driver, "Yes", config.response_timeout)
        print(f"[select_channel_2] Confirmation reply: {confirmation_reply}")
    except Exception as exc:
        return False, f"[select_channel_2] Error sending confirmation: {exc}"

    # ------------------------------------------------------------------
    # Step 8b: Wait for the bot to return to the main menu (second reply
    # after "Yes").  The bot sends two messages in sequence:
    #   [1] "Your preferred channel has been set to IOT."
    #   [2] The main menu again
    # We wait for [2] so the next flow starts with a clean conversation
    # state and does not pick up a stale reply.
    # ------------------------------------------------------------------
    post_confirmation_menu = wait_for_nth_reply(driver, 2, config.response_timeout)
    print(f"[select_channel_2] Post-confirmation main menu: {post_confirmation_menu}")

    # ------------------------------------------------------------------
    # Step 9: Validate success message and verify DB channel preference
    # ------------------------------------------------------------------
    try:
        connection = get_connection()
        try:
            passed, message = validate_channel_selection_success(
                confirmation_reply,
                channel_selection,
                lang_symbol,
                connection,
                config.user_number,
                _TARGET_CHANNEL,
            )
        finally:
            connection.close()
    except Exception as exc:
        return False, f"[select_channel_2] DB error during success validation: {exc}"

    if not passed:
        return False, f"[select_channel_2] Channel selection success validation failed: {message}"

    print("[select_channel_2] Channel selection success validation: PASSED")
    return True, ""
