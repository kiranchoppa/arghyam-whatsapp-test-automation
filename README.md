# JalShoochak WhatsApp Automation & Validation

This project automates sending a message to a WhatsApp bot via Selenium, captures
the bot's reply, and validates that reply against the expected menu options fetched
live from a PostgreSQL database.

---

## Project Layout

```text
Arghyam/
├── send_whatsapp.py                      # Entry point - run this to start the automation
├── glific_message_templates.json         # Static reference copy of the Glific flow JSON
├── requirements.txt
├── pytest.ini
├── .env                                  # Your local environment config (never commit this)
├── .env.example                          # Template for .env
│
├── src/
│   └── whatsapp_automation/
│       ├── __init__.py
│       ├── config.py                     # Loads and validates all env variables
│       ├── driver_factory.py             # Creates the Selenium browser driver
│       ├── messaging.py                  # WhatsApp Web send/receive helpers
│       ├── runner.py                     # Orchestrates the full automation flow
│       ├── queries.py                    # All SQL query strings as named constants
│       ├── db.py                         # Database connection and query execution
│       └── services/
│           ├── __init__.py
│           └── glific_service.py         # Glific template fetch, parse, and validation logic
│
└── tests/
    ├── conftest.py                       # Adds src/ to Python path for test imports
    └── test_whatsapp_web.py              # Unit tests + end-to-end Selenium test
```

---

## How the Automation Works — Step by Step

### 1. Entry point: `send_whatsapp.py`

Running `send_whatsapp.py` is the single command that triggers everything. It adds
`src/` to `sys.path` and calls `run_whatsapp_automation()` from `runner.py`.

```bash
.venv/bin/python send_whatsapp.py
```

---

### 2. Configuration loading: `config.py`

`runner.py` calls `load_config()` first. This function:

- Reads `.env` using `python-dotenv`.
- Validates every required value (phone number format, browser name, timeouts,
  database credentials).
- Returns a frozen `WhatsAppConfig` dataclass that is passed throughout the
  application.

All configuration for the entire run — WhatsApp settings, browser settings, and
database settings — lives in this single config object.

**Environment variables loaded here:**

| Variable | Purpose |
|---|---|
| `JALSHOOCHAK_WHATSAPP_NUMBER` | Recipient phone number in E.164 format (`+91...`) |
| `WHATSAPP_MESSAGE` | Text message to send to the bot |
| `WHATSAPP_BROWSER` | Browser to drive: `edge` or `chromium` |
| `EDGE_PROFILE_DIR` | Path to the persistent Edge profile (keeps WhatsApp logged in) |
| `EDGE_PROFILE_NAME` | Profile subfolder name (usually `Default`) |
| `SEND_TIMEOUT_SECONDS` | Max seconds to wait for the WhatsApp chat input to appear |
| `RESPONSE_TIMEOUT_SECONDS` | Max seconds to wait for the bot to reply |
| `DB_URL` | PostgreSQL connection URL (`postgresql://host:port/dbname` or `jdbc:postgresql://...`) |
| `DB_USERNAME` | Database username |
| `DB_PASSWORD` | Database password |
| `COMMON_SCHEMA` | PostgreSQL schema name (default: `common_schema`) |
| `TENT_CONFIG` | Table name holding tenant config (default: `tenant_config_master_table`) |
| `TENT_ID` | Tenant ID to query (default: `17`) |

---

### 3. Browser startup: `driver_factory.py`

`runner.py` calls `create_driver(browser, edge_profile_dir, edge_profile_name)`.

This creates a Selenium WebDriver pointed at the persistent browser profile. Using a
persistent profile means WhatsApp Web stays logged in between runs — no QR scan
required after the first setup.

---

### 4. Sending the message: `messaging.py`

`runner.py` calls two functions from `messaging.py`:

1. **`count_incoming_bubbles(driver)`** — counts how many incoming message bubbles
   are already on screen before the message is sent. This baseline is used later to
   detect a new reply.

2. **`send_message(driver, to_number, message, send_timeout)`** — navigates to
   `https://web.whatsapp.com/send?phone=<number>`, waits for the chat input box to
   appear (up to `SEND_TIMEOUT_SECONDS`), types the message, and presses Enter.

---

### 5. Waiting for the bot reply: `messaging.py`

`runner.py` calls **`wait_for_response(driver, bubbles_before, selector, response_timeout)`**.

This function polls WhatsApp Web until the number of incoming message bubbles
exceeds the pre-send count (i.e., a new reply arrived). Once detected — or after
`RESPONSE_TIMEOUT_SECONDS` — it scrolls to the bottom of the chat, reads the last
incoming bubble, and returns its text.

`extract_message_text(bubble)` is used internally to handle ordered list items
(numbered menu options) that WhatsApp renders as `<ol><li>` elements.

---

### 6. Validating the bot reply against the database: `services/glific_service.py`

After the bot response is captured, `runner.py` calls
`validate_item_selection(response_message, config)` from `glific_service.py`.

This is where the database integration happens. The function does three things:

#### a) Fetch the config from PostgreSQL

`fetch_glific_templates(config)` is called. Internally it:

1. Picks the `GET_TENANT_CONFIG_VALUE` query string from **`queries.py`**.
2. Substitutes `{schema}` and `{table}` with `COMMON_SCHEMA` and `TENT_CONFIG` from
   the config (identifier substitution via Python `str.format()` — these values come
   from env vars, not user input).
3. Calls **`db.get_connection()`** from `db.py` to open a `psycopg2` connection
   (JDBC-style `jdbc:postgresql://...` URLs are automatically normalised to
   `postgresql://...`).
4. Calls **`db.execute_query()`** from `db.py` with the formatted query and
   parameterised values `{tenant_id: 17, config_key: "GLIFIC_MESSAGE_TEMPLATES"}`.
5. Parses the returned `config_value` text column as JSON using
   `json.JSONDecoder().raw_decode()` (tolerant of any trailing characters in the
   stored value).

The database table being queried is:

```sql
SELECT config_value
FROM common_schema.tenant_config_master_table
WHERE tenant_id = 17
  AND config_key = 'GLIFIC_MESSAGE_TEMPLATES'
  AND deleted_at IS NULL;
```

The `config_value` column contains a JSON document describing all the screens and
messages of the Glific WhatsApp flow (see `glific_message_templates.json` for the
full reference structure).

#### b) Extract the expected menu options

`extract_item_selection_options(config_value)` navigates the parsed JSON:

```
config_value
  └── screens
        └── ITEM_SELECTION
              └── options
                    ├── OPTION_1 → label.en = "Submit Reading"
                    ├── OPTION_2 → label.en = "Report Issue"
                    ├── OPTION_3 → label.en = "Select Language"
                    └── OPTION_4 → label.en = "Select Channel"
```

It returns the English labels sorted by `order`, e.g.:
`["Submit Reading", "Report Issue", "Select Language", "Select Channel"]`

#### c) Compare against the bot response

Each expected label is checked for presence in the bot's response text:

- **`[PASS]`** — at least one option label is found in the response. This confirms
  the bot is sending the correct main menu.
- **`[FAIL]`** — no option label matches. The full response text is printed for
  diagnosis.

---

### 7. SQL query store: `queries.py`

All SQL strings are stored as named Python constants in a single file so they are
easy to find, reuse, and extend. Adding a new query means adding a new named
constant here.

```python
GET_TENANT_CONFIG_VALUE = """
SELECT config_value
FROM {schema}.{table}
WHERE tenant_id = %(tenant_id)s
  AND config_key = %(config_key)s
  AND deleted_at IS NULL;
"""
```

`{schema}` / `{table}` are Python format placeholders (identifier injection from
trusted env vars). `%(tenant_id)s` / `%(config_key)s` are psycopg2 parameterised
bindings (safe from SQL injection).

---

### 8. Database layer: `db.py`

A thin, stateless module with exactly two responsibilities:

- **`get_connection(db_url, db_username, db_password)`** — opens and returns a
  `psycopg2` connection. Accepts both `postgresql://` and `jdbc:postgresql://` URL
  formats.
- **`execute_query(conn, query, params)`** — executes a query against an open
  connection and returns all rows as a list of plain Python dicts. Does not open or
  close the connection; that is the caller's responsibility.

No SQL strings or business logic live here.

---

### 9. Static reference: `glific_message_templates.json`

A checked-in copy of the full Glific flow JSON (the same structure stored in
`config_value` in the database). This serves as:

- A human-readable reference of every screen, option, and message in the flow.
- A baseline for writing tests without a live database connection.

---

## Full Execution Flow Diagram

```
send_whatsapp.py
      │
      └─► runner.py: run_whatsapp_automation()
               │
               ├─► config.py: load_config()
               │        └── reads .env → returns WhatsAppConfig
               │
               ├─► driver_factory.py: create_driver()
               │        └── starts Edge/Chromium with persistent profile
               │
               ├─► messaging.py: count_incoming_bubbles()
               │        └── baseline incoming bubble count
               │
               ├─► messaging.py: send_message()
               │        └── opens WhatsApp Web, types message, sends
               │
               ├─► messaging.py: wait_for_response()
               │        └── polls until new bubble appears → returns text
               │
               └─► services/glific_service.py: validate_item_selection()
                        │
                        ├─► queries.py: GET_TENANT_CONFIG_VALUE
                        │        └── SQL string with {schema}/{table} placeholders
                        │
                        ├─► db.py: get_connection()
                        │        └── opens psycopg2 connection (normalises JDBC URL)
                        │
                        ├─► db.py: execute_query()
                        │        └── runs query, returns rows as list of dicts
                        │
                        ├─► parse config_value JSON (raw_decode, tolerant of trailing data)
                        │
                        ├─► extract_item_selection_options()
                        │        └── ["Submit Reading", "Report Issue", ...]
                        │
                        └─► compare options against bot response
                                 ├── [PASS] option found in response
                                 └── [FAIL] no option found, print response
```

---

## Setup

```bash
cd /home/bhcp0138/Documents/Arghyam
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and fill in your real values for all variables — especially the
WhatsApp number, browser profile path, and database credentials.

---

## Run

```bash
.venv/bin/python send_whatsapp.py
```

---

## Run Tests

Unit tests only (no browser required):

```bash
.venv/bin/pytest -m "not e2e"
```

Full suite including the live Selenium test:

```bash
.venv/bin/pytest -m "e2e or not e2e"
```

End-to-end test only:

```bash
.venv/bin/pytest -m e2e
```

---

## Notes

- The persistent browser profile at `EDGE_PROFILE_DIR` keeps WhatsApp Web
  authenticated between runs. On first use, open the browser manually, scan the
  QR code, and let WhatsApp Web load fully before running the script.
- `DB_URL` accepts both `postgresql://host:port/dbname` and
  `jdbc:postgresql://host:port/dbname` formats.
- The validation step is non-blocking — if the database is unreachable, a
  `[DB ERROR]` line is printed and the script exits cleanly.
- To add a new SQL query, add a named constant to `queries.py` and create a new
  service file under `services/` for its business logic.
