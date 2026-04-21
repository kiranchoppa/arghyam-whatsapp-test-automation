"""Top-level automation runner."""

import sys

from selenium.common.exceptions import WebDriverException

from whatsapp_automation.config import load_config
from whatsapp_automation.driver_factory import create_driver
from whatsapp_automation.messaging import (
    count_incoming_bubbles,
    send_message,
    wait_for_response,
)
from whatsapp_automation.services.glific_service import validate_item_selection


def run_whatsapp_automation():
    driver = None
    config = None
    try:
        config = load_config()
        driver = create_driver(
            browser=config.browser,
            edge_profile_dir=config.edge_profile_dir,
            edge_profile_name=config.edge_profile_name,
            keep_browser_open=config.keep_browser_open,
        )

        bubbles_before, bubble_selector = count_incoming_bubbles(driver)
        send_message(
            driver=driver,
            to_number=config.recipient_number,
            message=config.message,
            send_timeout=config.send_timeout,
        )
        print("Message sent!")
        print(f"Browser  : {config.browser}")
        print(f"To       : {config.recipient_number}")
        print(f"Send timeout     : {config.send_timeout}s")
        print(f"Response timeout : {config.response_timeout}s")

        response_message = wait_for_response(
            driver=driver,
            bubbles_before=bubbles_before,
            selector=bubble_selector,
            response_timeout=config.response_timeout,
        )
        print("\nLatest incoming message:")
        print(response_message)

        validate_item_selection(response_message, config)
        return 0
    except WebDriverException as exc:
        print(
            "Could not start browser session. Close existing Edge windows using the same "
            "profile and retry.",
            file=sys.stderr,
        )
        print(str(exc), file=sys.stderr)
        return 2
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    finally:
        if driver and not (config and config.keep_browser_open):
            driver.quit()

