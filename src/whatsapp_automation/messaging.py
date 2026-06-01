"""Messaging lifecycle helpers — open, send/receive, close."""

import time

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def open_whatsapp(driver, to_number: str, send_timeout: int) -> None:
    """Navigate to the WhatsApp Web chat for *to_number* and wait for the input box.

    Args:
        driver:       Selenium WebDriver instance (browser already open).
        to_number:    Recipient phone number, with or without a leading '+'.
        send_timeout: Maximum seconds to wait for the chat input box to appear.

    Raises:
        RuntimeError: If the chat input box does not appear within *send_timeout*
                      seconds (e.g. QR code not yet scanned).
    """
    phone_digits = to_number.replace("+", "")
    driver.get(f"https://web.whatsapp.com/send?phone={phone_digits}")
    try:
        WebDriverWait(driver, send_timeout).until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"]'))
        )
    except TimeoutException as exc:
        raise RuntimeError(
            f"Chat box did not appear within {send_timeout}s. "
            "WhatsApp Web may not be ready — scan QR/login and try again."
        ) from exc


def send_message(driver, message: str, response_timeout: int) -> str:
    """Type *message* into the already-open chat box, send it, and return the bot reply.

    Relies on ``open_whatsapp`` having been called first so that the chat input
    box is present in the DOM.

    Uses the XPath ``following::`` axis anchored on the last ``message-out``
    element to find the first ``message-in`` that arrives after our message.
    This avoids attribute-based detection entirely and is robust against
    WhatsApp Web's virtual/windowed DOM rendering, repeated message text, and
    multi-message bot replies.

    Args:
        driver:           Selenium WebDriver instance with an open chat.
        message:          Text to send.
        response_timeout: Maximum seconds to wait for the bot reply.

    Returns:
        The bot reply text, or an empty string if no reply arrives in time.
    """
    box = driver.find_element(By.XPATH, '//div[@contenteditable="true"]')
    box.click()
    box.send_keys(message)
    box.send_keys(Keys.ENTER)

    time.sleep(2)  # let our message-out settle in the DOM before anchoring

    reply_xpath = (
        '(//div[contains(@class,"message-out")])[last()]'
        '/following::div[contains(@class,"message-in")][1]'
    )

    def _bot_replied(drv):
        return len(drv.find_elements(By.XPATH, reply_xpath)) > 0

    try:
        WebDriverWait(driver, response_timeout).until(_bot_replied)
    except TimeoutException:
        return ""

    reply_els = driver.find_elements(By.XPATH, reply_xpath)
    return reply_els[0].text.strip() if reply_els else ""


def wait_for_nth_reply(driver, nth: int, response_timeout: int) -> str:
    """Wait for the *nth* incoming message after the last outgoing message.

    Use this when the bot sends multiple replies to a single message and you
    need to wait for a specific one.  The anchor is the same as in
    ``send_message`` — the last ``message-out`` element — so call this
    immediately after ``send_message`` returns, without sending anything else.

    Args:
        driver:           Selenium WebDriver instance with an open chat.
        nth:              Which incoming message to return (1-based).
                          ``nth=1`` is identical to what ``send_message`` already
                          returns; use ``nth=2`` to get the second reply, etc.
        response_timeout: Maximum seconds to wait for the nth reply to appear.

    Returns:
        The bot reply text, or an empty string if it does not arrive in time.
    """
    reply_xpath = (
        f'(//div[contains(@class,"message-out")])[last()]'
        f'/following::div[contains(@class,"message-in")][{nth}]'
    )

    def _reply_arrived(drv):
        return len(drv.find_elements(By.XPATH, reply_xpath)) > 0

    try:
        WebDriverWait(driver, response_timeout).until(_reply_arrived)
    except TimeoutException:
        return ""

    reply_els = driver.find_elements(By.XPATH, reply_xpath)
    return reply_els[0].text.strip() if reply_els else ""


def close_whatsapp(driver) -> None:
    """Quit the browser and close the WhatsApp Web session.

    Args:
        driver: Selenium WebDriver instance to shut down.
    """
    driver.quit()
