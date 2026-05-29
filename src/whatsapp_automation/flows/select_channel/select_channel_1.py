"""select_channel flow — test scenario 1."""

from whatsapp_automation.db import get_connection
from whatsapp_automation.messaging import send_message
from whatsapp_automation.services.select_channel_service import get_main_menu
from whatsapp_automation.validations.common_validations import validate_main_menu


def run(driver, config):
    """Test scenario 1 for the select_channel flow."""
    expected_main_menu = None

    try:
        connection = get_connection()
        try:
            expected_main_menu = get_main_menu(connection, config.user_number)
        finally:
            connection.close()
    except Exception as exc:
        print(f"[select_channel_1] DB/service error while fetching main menu: {exc}")
        return

    try:
        response = send_message(
            driver=driver,
            to_number=config.recipient_number,
            message=config.start_message,
            send_timeout=config.send_timeout,
            response_timeout=config.response_timeout,
        )
        print(f"[select_channel_1] Response: {response}")
    except Exception as exc:
        print(f"[select_channel_1] Error during send/receive: {exc}")
        return

    passed, message = validate_main_menu(response, expected_main_menu)
    if passed:
        print("[select_channel_1] Main menu validation: PASSED")
    else:
        print(f"[select_channel_1] Main menu validation: FAILED\n{message}")
