"""Tests for WhatsApp Selenium automation."""

from __future__ import annotations

import pytest

from whatsapp_automation.config import validate_phone
from whatsapp_automation.messaging import extract_message_text
from whatsapp_automation.runner import run_whatsapp_automation


class FakeItem:
    def __init__(self, text: str):
        self.text = text


class FakeBubble:
    def __init__(self, text: str, items: list[str]):
        self.text = text
        self._items = [FakeItem(item) for item in items]

    def find_elements(self, by, selector):  # noqa: ARG002
        return self._items


def test_validate_phone_accepts_e164():
    assert validate_phone("+918971100150", "TEST") == "+918971100150"


def test_validate_phone_rejects_missing_plus():
    with pytest.raises(ValueError, match="must start with"):
        validate_phone("918971100150", "TEST")


def test_extract_message_text_numbers_ordered_list():
    bubble = FakeBubble(
        text="Please select:\nSubmit Reading\nReport Issue",
        items=["Submit Reading", "Report Issue"],
    )
    parsed = extract_message_text(bubble)
    assert "1. Submit Reading" in parsed
    assert "2. Report Issue" in parsed


@pytest.mark.e2e
def test_whatsapp_end_to_end():
    """Runs the actual Selenium flow against WhatsApp Web."""
    assert run_whatsapp_automation() == 0

