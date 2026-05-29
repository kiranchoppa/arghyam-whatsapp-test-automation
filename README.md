# WhatsApp Selenium Automation

This project now contains only the core automation flow:

1. Open WhatsApp Web in Selenium
2. Send a message to the configured number
3. Wait for and print the latest incoming reply

All DB validation and language-selection flow code has been removed.

## Project Layout

```text
Arghyam/
├── send_whatsapp.py
├── requirements.txt
├── .env.example
├── src/
│   └── whatsapp_automation/
│       ├── __init__.py
│       ├── config.py
│       ├── driver_factory.py
│       ├── messaging.py
│       └── runner.py
```

## Environment Variables

Set these in `.env`:

- `JALSHOOCHAK_WHATSAPP_NUMBER` (E.164 format, e.g. `+91...`)
- `APP_ENV` (`dev` or `staging`; optional context for your environment)
- `START_MESSAGE` (message to send, e.g. `start` or `startstaging`)
- `WHATSAPP_BROWSER` (`edge` or `chromium`)
- `EDGE_PROFILE_DIR`
- `EDGE_PROFILE_NAME` (usually `Default`)
- `KEEP_BROWSER_OPEN` (`true` or `false`)
- `SEND_TIMEOUT_SECONDS`
- `RESPONSE_TIMEOUT_SECONDS`

## Setup

```bash
cd /home/bhcp0138/Documents/Arghyam
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

## Run

```bash
.venv/bin/python send_whatsapp.py
```
