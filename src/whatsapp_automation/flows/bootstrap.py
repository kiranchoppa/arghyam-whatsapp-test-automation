"""Shared bootstrap helper for all flows.

Every flow that needs a fresh bot session calls ``bootstrap_flow`` at the
start.  It sends the configured start message, validates the main menu
reply against DB expectations, and returns the main menu data so the
calling flow can use it without a second DB round-trip.
"""

from whatsapp_automation.db import get_connection
from whatsapp_automation.messaging import send_message
from whatsapp_automation.services.common_service import (
    SELECT_CHANNEL_LABEL,
    SELECT_LANGUAGE_LABEL,
    get_main_menu,
)
from whatsapp_automation.validations.common_validations import validate_main_menu


def bootstrap_flow(
    driver, config, menu_context: dict | None = None
) -> tuple[bool, str, dict | None]:
    """Send the start message, validate the main menu reply.

    Steps:
    1. Open a DB connection and fetch main menu data (ITEM_SELECTION +
       lang_symbol) for ``config.user_number``.  Connection is closed
       immediately after.
    2. Build a ``hidden_labels`` set from *menu_context* — the localised
       labels of options that are legitimately absent for this tenant (e.g.
       "Select Channel" when only one channel is configured).
    3. Send ``config.start_message`` and wait for the bot reply.
    4. Validate the reply against the DB-backed main menu expectations,
       skipping any labels in ``hidden_labels``.

    Args:
        driver:       Selenium WebDriver instance with an already-open WhatsApp chat.
        config:       ``WhatsAppConfig`` loaded from ``.env``.
        menu_context: Optional dict produced by ``validate_flows`` indicating
                      which conditional options are visible, e.g.::

                          {
                              "select_channel_visible": True,
                              "select_language_visible": False,
                          }

                      When ``None`` or omitted all options are validated
                      (safe default for single-flow callers).

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

    lang_symbol = main_menu["lang_symbol"]

    # Translate menu_context visibility flags into localised label strings
    # that validate_main_menu should skip.
    ctx = menu_context or {}
    hidden_labels: set[str] = set()
    if not ctx.get("select_channel_visible", True):
        hidden_labels.add(
            SELECT_CHANNEL_LABEL.get(lang_symbol, SELECT_CHANNEL_LABEL["en"])
        )
    if not ctx.get("select_language_visible", True):
        hidden_labels.add(
            SELECT_LANGUAGE_LABEL.get(lang_symbol, SELECT_LANGUAGE_LABEL["en"])
        )

    try:
        start_reply = send_message(driver, config.start_message, config.response_timeout)
        print(f"[bootstrap] Start reply: {start_reply}")
    except Exception as exc:
        return False, f"Error sending start message: {exc}", None

    passed, message = validate_main_menu(start_reply, main_menu, hidden_labels)
    if not passed:
        return False, f"Main menu validation failed: {message}", None

    print("[bootstrap] Main menu validation: PASSED")
    return True, "", main_menu
