"""select_channel flow — hidden test (single-channel tenants).

Steps
-----
1.  DB: resolve the user's language symbol.
2.  Send the start message and receive the main menu reply.
3.  Assert the localised "Select Channel" label is NOT present in the reply.
    When only one channel is configured the bot should not expose this option.
"""

from whatsapp_automation.db import get_connection
from whatsapp_automation.messaging import send_message
from whatsapp_automation.services.common_service import SELECT_CHANNEL_LABEL, get_main_menu


def run(driver, config) -> tuple[bool, str]:
    """Test that "Select Channel" is absent from the main menu (single-channel tenant).

    Does not use bootstrap_flow because validate_main_menu checks all DB config
    options — including "Select Channel" — against the bot reply, which would
    incorrectly fail when the bot correctly hides the option.

    Returns:
        ``(True, "")`` on full pass, ``(False, reason)`` on any failure.
    """
    # ------------------------------------------------------------------
    # Step 1: DB — resolve language symbol (needed for the keyword check)
    # ------------------------------------------------------------------
    try:
        connection = get_connection()
        try:
            main_menu = get_main_menu(connection, config.user_number)
        finally:
            connection.close()
    except Exception as exc:
        return False, f"[select_channel_hidden] DB error: {exc}"

    lang_symbol = main_menu["lang_symbol"]

    # ------------------------------------------------------------------
    # Step 2: Send start message and receive the main menu reply
    # ------------------------------------------------------------------
    try:
        start_reply = send_message(driver, config.start_message, config.response_timeout)
        print(f"[select_channel_hidden] Start reply: {start_reply}")
    except Exception as exc:
        return False, f"[select_channel_hidden] Error sending start message: {exc}"

    # ------------------------------------------------------------------
    # Step 3: Assert "Select Channel" label is NOT present in the reply
    # ------------------------------------------------------------------
    keyword = SELECT_CHANNEL_LABEL.get(lang_symbol, SELECT_CHANNEL_LABEL["en"])
    if keyword.lower() in start_reply.lower():
        return False, (
            f"[select_channel_hidden] 'Select Channel' option found in main menu "
            f"but should be hidden when only one channel is configured.\n"
            f"  Found keyword : {keyword!r}\n"
            f"  Response      : {start_reply!r}"
        )

    print(
        "[select_channel_hidden] 'Select Channel' option correctly absent from main menu: PASSED"
    )
    return True, ""
