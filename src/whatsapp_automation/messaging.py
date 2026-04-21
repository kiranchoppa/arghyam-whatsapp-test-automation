"""Messaging and response parsing helpers."""

import time

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def send_message(driver, to_number, message, send_timeout):
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


def extract_message_text(bubble):
    list_items = bubble.find_elements(By.XPATH, ".//ol/li")
    if not list_items:
        return bubble.text.strip()

    full_text = bubble.text.strip()
    for i, item in enumerate(list_items, start=1):
        item_text = item.text.strip()
        full_text = full_text.replace(item_text, f"{i}. {item_text}", 1)
    return full_text


def count_incoming_bubbles(driver):
    for selector in (
        '//div[contains(@class,"message-in")]',
        '//*[@data-testid="msg-container"]',
    ):
        elements = driver.find_elements(By.XPATH, selector)
        if elements:
            return len(elements), selector
    return 0, '//div[contains(@class,"message-in")]'


def wait_for_response(driver, bubbles_before, selector, response_timeout):
    print(f"Waiting for bot response (max {response_timeout}s)...")
    try:
        WebDriverWait(driver, response_timeout).until(
            lambda d: len(d.find_elements(By.XPATH, selector)) > bubbles_before
        )
        print("Response received!")
    except TimeoutException:
        print(f"No new response within {response_timeout}s - reading latest message anyway.")

    driver.execute_script(
        "var el = document.querySelector('#main'); if(el) el.scrollTop = el.scrollHeight;"
    )
    time.sleep(1)

    bubbles = driver.find_elements(By.XPATH, selector)
    if bubbles:
        return extract_message_text(bubbles[-1])
    return "No incoming message found."
