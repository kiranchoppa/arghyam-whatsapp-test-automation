"""no_water_supply flow — test scenario 3 (Others / invalid reason with colon).

Steps
-----
1.  Bootstrap: send start message, validate main menu (DB + WhatsApp).
2.  DB: fetch supply outage reasons from SUPPLY_OUTAGE_REASONS tenant config.
3.  Identify the option number associated with "Report Issue" in the main menu.
4.  Send that number and receive the issue-type sub-menu reply.
5.  Identify the option number for "No Water Supply" from the sub-menu reply.
6.  Send that number and receive the outage-reason list prompt.
7.  Validate that all configured outage reasons are present in the prompt.
8.  Find and send the option number for "Others" from the reasons prompt.
9.  Validate the bot replies with "Please report your issue."
10. Compose an invalid reason that contains ":" (e.g. "HH:MM" time format),
    capture an IST-aware timestamp, then send the message.
11. Validate the bot replies with the expected validation error:
    "Issue reason can only contain letters, numbers, and spaces."
12. Open the analytics DB and verify NO new anomaly row was created after
    *sent_at* — confirming the invalid submission was rejected.
"""

import re
from datetime import datetime, timedelta, timezone

from whatsapp_automation.db import get_connection
from whatsapp_automation.flows.bootstrap import bootstrap_flow
from whatsapp_automation.messaging import send_message
from whatsapp_automation.services.no_water_supply_service import (
    ANOMALY_SCHEME_ID,
    ANOMALY_USER_ID,
    NO_WATER_SUPPLY_LABEL,
    REPORT_ISSUE_LABEL,
    get_analytics_connection,
    get_outage_reasons,
)
from whatsapp_automation.validations.no_water_supply_validations import (
    validate_no_anomaly_record,
    validate_outage_reasons_prompt,
)

IST = timezone(timedelta(hours=5, minutes=30))

# Bot error message expected when the reason contains disallowed characters.
INVALID_REASON_PHRASE = "Issue reason can only contain letters, numbers, and spaces"

# Phrase the bot must reply with after "Others" is selected.
PLEASE_REPORT_PHRASE = "Please report your issue"

# Label used to locate the "Others" option in the reasons list.
_OTHERS_LABEL = "Others"


_TIME_PATTERN = re.compile(r"^\s*\d{1,2}:\d{2}\s*(am|pm)\s*$", re.IGNORECASE)


def _find_option_by_label(
    options: dict, label_map: dict[str, str], lang_symbol: str
) -> str | None:
    """Return the option number whose DB label best matches an entry in *label_map*.

    Tries the localised label first, then falls back to English.
    """
    def _search(keyword: str, sym: str) -> str | None:
        for key, option in options.items():
            label = option.get("label", {}).get(sym, "")
            if keyword.lower() in label.lower():
                match = re.search(r"\d+$", key)
                return match.group() if match else key
        return None

    keyword = label_map.get(lang_symbol, label_map["en"])
    result = _search(keyword, lang_symbol)
    if result is not None:
        return result
    if lang_symbol != "en":
        return _search(label_map["en"], "en")
    return None


def _option_lines(reply: str) -> list[str]:
    """Return non-prompt, non-timestamp lines from a WhatsApp list reply.

    The first non-timestamp line is always the prompt and is skipped.
    """
    lines = [line.strip() for line in reply.splitlines() if line.strip()]
    option_lines: list[str] = []
    prompt_seen = False
    for line in lines:
        if _TIME_PATTERN.match(line):
            continue
        if not prompt_seen:
            prompt_seen = True
            continue
        option_lines.append(line)
    return option_lines


def _find_option_in_reply(
    reply: str, label_map: dict[str, str], lang_symbol: str
) -> str | None:
    """Scan *reply* for a list item matching a label in *label_map*.

    Tries the localised keyword first, then English.  Supports both numbered
    lines and unnumbered lines (position-based fallback).
    """
    keywords: list[str] = [label_map.get(lang_symbol, label_map["en"])]
    if lang_symbol != "en":
        keywords.append(label_map["en"])

    lines = reply.splitlines()

    for keyword in keywords:
        for line in lines:
            if keyword.lower() not in line.lower():
                continue
            match = re.match(r"^\s*(\d+)[.):\s]", line)
            if match:
                return match.group(1)

        for index, line in enumerate(_option_lines(reply), start=1):
            text = re.sub(r"^\s*\d+[.):\s]+", "", line)
            if keyword.lower() in text.lower() or keyword.lower() in line.lower():
                return str(index)

    return None


def run(driver, config, menu_context: dict | None = None) -> tuple[bool, str]:
    """Test scenario 3 for the no_water_supply flow — Others with invalid reason.

    Returns:
        ``(True, "")`` on full pass, ``(False, reason)`` on any failure.
    """
    # ------------------------------------------------------------------
    # Step 1: Bootstrap — send start message + validate main menu
    # ------------------------------------------------------------------
    ok, err, main_menu = bootstrap_flow(driver, config, menu_context)
    if not ok:
        return False, f"[no_water_supply_3] Bootstrap failed: {err}"

    lang_symbol = main_menu["lang_symbol"]

    # ------------------------------------------------------------------
    # Step 2: DB — fetch outage reasons
    # ------------------------------------------------------------------
    try:
        connection = get_connection()
        try:
            reasons = get_outage_reasons(connection)
        finally:
            connection.close()
    except Exception as exc:
        return False, f"[no_water_supply_3] DB/service error: {exc}"

    if not reasons:
        return False, "[no_water_supply_3] No outage reasons found in SUPPLY_OUTAGE_REASONS config."

    others_reason = next(
        (r for r in reasons if r.get("id", "").upper() == "OTHERS"), None
    )
    if others_reason is None:
        return False, "[no_water_supply_3] 'OTHERS' reason not found in SUPPLY_OUTAGE_REASONS config."

    print(
        f"[no_water_supply_3] {len(reasons)} outage reason(s) loaded. "
        f"'Others' entry: {others_reason!r}"
    )

    # ------------------------------------------------------------------
    # Step 3: Identify "Report Issue" option number in main menu
    # ------------------------------------------------------------------
    report_issue_number = _find_option_by_label(
        main_menu["item_selection"]["options"], REPORT_ISSUE_LABEL, lang_symbol
    )
    if report_issue_number is None:
        return False, (
            f"[no_water_supply_3] Could not find 'Report Issue' option in main menu.\n"
            f"  Labels tried: {REPORT_ISSUE_LABEL}"
        )
    print(f"[no_water_supply_3] 'Report Issue' option number: {report_issue_number}")

    # ------------------------------------------------------------------
    # Step 4: Send "Report Issue" option, receive issue-type sub-menu
    # ------------------------------------------------------------------
    try:
        report_issue_reply = send_message(driver, report_issue_number, config.response_timeout)
        print(f"[no_water_supply_3] Report Issue reply: {report_issue_reply}")
    except Exception as exc:
        return False, f"[no_water_supply_3] Error sending 'Report Issue' option: {exc}"

    # ------------------------------------------------------------------
    # Step 5: Identify "No Water Supply" option in sub-menu reply
    # ------------------------------------------------------------------
    no_water_number = _find_option_in_reply(
        report_issue_reply, NO_WATER_SUPPLY_LABEL, lang_symbol
    )
    if no_water_number is None:
        return False, (
            f"[no_water_supply_3] Could not find 'No Water Supply' option in reply.\n"
            f"  Labels tried: {NO_WATER_SUPPLY_LABEL}\n"
            f"  Reply: {report_issue_reply!r}"
        )
    print(f"[no_water_supply_3] 'No Water Supply' option number: {no_water_number}")

    # ------------------------------------------------------------------
    # Step 6: Send "No Water Supply" option, receive outage-reason list
    # ------------------------------------------------------------------
    try:
        reasons_reply = send_message(driver, no_water_number, config.response_timeout)
        print(f"[no_water_supply_3] Outage reasons reply: {reasons_reply}")
    except Exception as exc:
        return False, f"[no_water_supply_3] Error sending 'No Water Supply' option: {exc}"

    # ------------------------------------------------------------------
    # Step 7: Validate outage reasons prompt
    # ------------------------------------------------------------------
    passed, message = validate_outage_reasons_prompt(reasons_reply, reasons)
    if not passed:
        return False, f"[no_water_supply_3] Outage reasons prompt validation failed: {message}"
    print("[no_water_supply_3] Outage reasons prompt validation: PASSED")

    # ------------------------------------------------------------------
    # Step 8: Find and send "Others" option number from the reasons list
    # ------------------------------------------------------------------
    others_label_map = {"en": _OTHERS_LABEL}
    others_number = _find_option_in_reply(reasons_reply, others_label_map, lang_symbol)
    if others_number is None:
        return False, (
            f"[no_water_supply_3] Could not find 'Others' option in reasons reply.\n"
            f"  Reply: {reasons_reply!r}"
        )
    print(f"[no_water_supply_3] 'Others' option number: {others_number}")

    try:
        please_report_reply = send_message(driver, others_number, config.response_timeout)
        print(f"[no_water_supply_3] After 'Others' reply: {please_report_reply}")
    except Exception as exc:
        return False, f"[no_water_supply_3] Error sending 'Others' option: {exc}"

    # ------------------------------------------------------------------
    # Step 9: Validate "Please report your issue." prompt
    # ------------------------------------------------------------------
    if PLEASE_REPORT_PHRASE.lower() not in please_report_reply.lower():
        return False, (
            f"[no_water_supply_3] Expected '{PLEASE_REPORT_PHRASE}' not found in reply.\n"
            f"  Reply: {please_report_reply!r}"
        )
    print("[no_water_supply_3] 'Please report your issue' prompt validation: PASSED")

    # ------------------------------------------------------------------
    # Step 10: Send an invalid reason that contains ":" — deliberately
    # triggers the bot's input validation.  Capture the timestamp just
    # before sending so the DB check excludes any pre-existing rows.
    # ------------------------------------------------------------------
    sent_at = datetime.now(tz=IST)
    invalid_reason = f"Test issue {sent_at.strftime('%H:%M')}"
    print(
        f"[no_water_supply_3] Sending invalid reason at {sent_at.isoformat()}: "
        f"{invalid_reason!r}"
    )

    try:
        error_reply = send_message(driver, invalid_reason, config.response_timeout)
        print(f"[no_water_supply_3] Error reply: {error_reply}")
    except Exception as exc:
        return False, f"[no_water_supply_3] Error sending invalid reason: {exc}"

    # ------------------------------------------------------------------
    # Step 11: Validate the bot's rejection message
    # ------------------------------------------------------------------
    if INVALID_REASON_PHRASE.lower() not in error_reply.lower():
        return False, (
            f"[no_water_supply_3] Expected validation error not found in reply.\n"
            f"  Expected : {INVALID_REASON_PHRASE!r}\n"
            f"  Reply    : {error_reply!r}"
        )
    print("[no_water_supply_3] Invalid reason rejection message validation: PASSED")

    # ------------------------------------------------------------------
    # Step 12: Confirm no anomaly row was written to analytics DB
    # ------------------------------------------------------------------
    try:
        analytics_conn = get_analytics_connection()
        try:
            passed, message = validate_no_anomaly_record(
                analytics_conn, ANOMALY_USER_ID, ANOMALY_SCHEME_ID, sent_at
            )
        finally:
            analytics_conn.close()
    except Exception as exc:
        return False, f"[no_water_supply_3] Analytics DB error: {exc}"

    if not passed:
        return False, f"[no_water_supply_3] DB absence check failed: {message}"

    print("[no_water_supply_3] No anomaly row written for invalid input: PASSED")
    return True, ""
