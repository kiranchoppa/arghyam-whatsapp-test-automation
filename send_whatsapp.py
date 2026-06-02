#!/usr/bin/env python3
"""Entry point for WhatsApp Selenium automation."""

import sys
from pathlib import Path

src_dir = Path(__file__).resolve().parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from whatsapp_automation.runner import run_whatsapp_automation  # noqa: E402


# ── Configure which flows to run ─────────────────────────────────────────────
# Add or remove keys from this list to control which flow tests are executed.
# Keys must match entries in src/whatsapp_automation/flows/flow_registry.py.
#
# Examples:
#   flows = ["select_channel_1"]               # run only scenario 1
#   flows = ["select_channel_1", "select_channel_2"]  # run both in order
#   flows = []                                 # run default send-and-read flow
FLOWS = [
    "select_channel_1",
    "select_channel_2",
    "select_channel_3"
]


def main():
    return run_whatsapp_automation(flows=FLOWS)


if __name__ == "__main__":
    raise SystemExit(main())
