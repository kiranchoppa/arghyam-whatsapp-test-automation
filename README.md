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

**Main database (jalsoochak):**
- `DB_URL` — primary PostgreSQL URL
- `DB_USERNAME`, `DB_PASSWORD`

**Analytics database (used by `no_water_supply_1`):**
- `ANALYTICS_DB_URL` — e.g. `postgresql://192.168.6.150:5432/analytics`
- `ANALYTICS_DB_USERNAME`, `ANALYTICS_DB_PASSWORD`
- `ANOMALY_USER_ID` — `user_id` filter for `analytics_schema.anomaly_table` (default `21350`)
- `ANOMALY_SCHEME_ID` — `scheme_id` filter (default `27653`)

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
