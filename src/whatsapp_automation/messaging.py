"""Messaging send/receive helpers."""

import time

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def send_message(driver, to_number, message, send_timeout, response_timeout) -> str:
    """Navigate to the chat, send a message, wait for the bot reply, and return it.

    After sending, uses the XPath ``following::`` axis anchored on the last
    ``message-out`` element to find the first ``message-in`` that arrives after
    our message. This avoids attribute-based detection entirely and is robust
    against WhatsApp Web's virtual/windowed DOM rendering, repeated message
    text, and multi-message bot replies.
    """
    phone_digits = to_number.replace("+", "")
    driver.get(f"https://web.whatsapp.com/send?phone={phone_digits}")
    try:
        box = WebDriverWait(driver, send_timeout).until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"]'))
        )
    except TimeoutException as exc:
        raise RuntimeError(
            f"Chat box did not appear within {send_timeout}s. "
            "WhatsApp Web may not be ready - scan QR/login and try again."
        ) from exc

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
