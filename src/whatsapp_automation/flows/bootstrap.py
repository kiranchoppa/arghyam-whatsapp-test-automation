"""Shared bootstrap helper for all flows.

Every flow that needs a fresh bot session calls ``bootstrap_flow`` at the
start.  It sends the configured start message, validates the main menu
reply against DB expectations, and returns the main menu data so the
calling flow can use it without a second DB round-trip.
"""

from whatsapp_automation.db import get_connection
from whatsapp_automation.messaging import send_message
from whatsapp_automation.services.common_service import get_main_menu
from whatsapp_automation.validations.common_validations import validate_main_menu


def bootstrap_flow(driver, config) -> tuple[bool, str, dict | None]:
    """Send the start message, validate the main menu reply.

    Steps:
    1. Open a DB connection and fetch main menu data (ITEM_SELECTION +
       lang_symbol) for ``config.user_number``.  Connection is closed
       immediately after.
    2. Send ``config.start_message`` and wait for the bot reply.
    3. Validate the reply against the DB-backed main menu expectations.

    Args:
        driver: Selenium WebDriver instance with an already-open WhatsApp chat.
        config: ``WhatsAppConfig`` loaded from ``.env``.

    Returns:
        ``(True, "", main_menu)`` on full success, where *main_menu* is the
        dict returned by ``get_main_menu`` (keys: ``item_selection``,
        ``lang_symbol``).

        ``(False, reason, None)`` if any step fails, where *reason* is a
        human-readable description of the failure.
    """
    main_menu = None

    try:
        connection = get_connection()
        try:
            main_menu = get_main_menu(connection, config.user_number)
        finally:
            connection.close()
    except Exception as exc:
        return False, f"DB error during bootstrap: {exc}", None

    try:
        start_reply = send_message(driver, config.start_message, config.response_timeout)
        print(f"[bootstrap] Start reply: {start_reply}")
    except Exception as exc:
        return False, f"Error sending start message: {exc}", None

    passed, message = validate_main_menu(start_reply, main_menu)
    if not passed:
        return False, f"Main menu validation failed: {message}", None

    print("[bootstrap] Main menu validation: PASSED")
    return True, "", main_menu
