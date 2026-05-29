"""Message formatting helpers kept separate from send/receive logic."""

from selenium.webdriver.common.by import By


def format_message_with_numbered_list(bubble):
    """Format a WhatsApp bubble text by numbering ordered-list items."""
    list_items = bubble.find_elements(By.XPATH, ".//ol/li")
    if not list_items:
        return bubble.text.strip()

    full_text = bubble.text.strip()
    for i, item in enumerate(list_items, start=1):
        item_text = item.text.strip()
        full_text = full_text.replace(item_text, f"{i}. {item_text}", 1)
    return full_text
