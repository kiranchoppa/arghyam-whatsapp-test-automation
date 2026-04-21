#!/usr/bin/env python3
"""Backward-compatible entrypoint for WhatsApp Selenium automation."""

import sys
from pathlib import Path

src_dir = Path(__file__).resolve().parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from whatsapp_automation.runner import run_whatsapp_automation


if __name__ == "__main__":
    raise SystemExit(run_whatsapp_automation())
