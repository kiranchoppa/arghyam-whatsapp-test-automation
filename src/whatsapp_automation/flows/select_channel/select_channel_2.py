"""select_channel flow — test scenario 2."""

from whatsapp_automation.messaging import send_message


def run(driver, config):
    """Test scenario 2 for the select_channel flow."""
    response = send_message(
        driver=driver,
        to_number=config.recipient_number,
        message=config.start_message,
        send_timeout=config.send_timeout,
        response_timeout=config.response_timeout,
    )

    print(f"[select_channel_2] Response: {response}")

    # TODO: add assertions once the expected response is known
    # e.g. assert "expected text" in response, f"Unexpected: {response!r}"
