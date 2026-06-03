"""no_water_supply flow — test scenario 1.

Steps
-----
1.  Bootstrap: send start message, validate main menu (DB + WhatsApp).
2.  DB: fetch supply outage reasons from SUPPLY_OUTAGE_REASONS tenant config.
3.  Identify the option number associated with "Report Issue" in the main menu.
4.  Send that number and receive the issue-type sub-menu reply.
5.  Identify the option number for "No Water Supply" from the sub-menu reply.
6.  Send that number and receive the outage-reason list prompt.
7.  Validate that all configured outage reasons are present in the prompt.
8.  Capture an IST-aware timestamp, then send "1" to select reason option 1.
9.  Receive the confirmation reply.
10. Open the analytics DB and verify a new anomaly row exists with
    created_at > sent_at for the configured user_id and scheme_id.
"""

import re
from datetime import datetime, timedelta, timezone

from whatsapp_automation.db import get_connection
from whatsapp_automation.flows.bootstrap import bootstrap_flow
from whatsapp_automation.messaging import send_message, wait_for_nth_reply
from whatsapp_automation.services.no_water_supply_service import (
    ANOMALY_SCHEME_ID,
    ANOMALY_USER_ID,
    NO_WATER_SUPPLY_LABEL,
    REPORT_ISSUE_LABEL,
    get_analytics_connection,
    get_outage_reasons,
)
from whatsapp_automation.validations.no_water_supply_validations import (
    validate_anomaly_record,
    validate_outage_reasons_prompt,
)

IST = timezone(timedelta(hours=5, minutes=30))


def _find_option_by_label(
    options: dict, label_map: dict[str, str], lang_symbol: str
) -> str | None:
    """Return the option number whose DB label best matches an entry in *label_map*.

    Tries the localised label first (``label_map[lang_symbol]`` searched against
    option labels for *lang_symbol*).  If nothing matches — e.g. because the
    localised keyword is slightly off — falls back to the English keyword
    (``label_map["en"]``) searched against English option labels so a
    translation mismatch never causes a silent failure.

    Args:
        options:     The ``options`` dict from the ITEM_SELECTION screen,
                     keyed by option number strings (e.g. ``{"1": {...}, ...}``).
        label_map:   Dict mapping language symbols to localised keywords,
                     e.g. ``REPORT_ISSUE_LABEL``.  Must contain ``"en"``.
        lang_symbol: ISO language symbol resolved for the user (e.g. ``"en"``).

    Returns:
        The matching option number string (e.g. ``"3"``), or ``None`` if not found
        in either the localised or English labels.
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


_TIME_PATTERN = re.compile(r"^\s*\d{1,2}:\d{2}\s*(am|pm)\s*$", re.IGNORECASE)


def _option_lines(reply: str) -> list[str]:
    """Return non-prompt, non-timestamp lines from a WhatsApp list reply.

    WhatsApp Web often strips leading ``1.``, ``2.`` prefixes from captured
    message text, so callers infer option numbers from line order instead.

    The first non-timestamp line is always the prompt (question/instruction)
    and is skipped regardless of its ending punctuation.
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
    lines (``4. No Water Supply``) and unnumbered lines where WhatsApp Web
    stripped the prefix — in that case the 1-based line index is returned.
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
    """Test scenario 1 for the no_water_supply flow.

    Returns:
        ``(True, "")`` on full pass, ``(False, reason)`` on any failure.
    """
    # ------------------------------------------------------------------
    # Step 1: Bootstrap — send start message + validate main menu
    # ------------------------------------------------------------------
    ok, err, main_menu = bootstrap_flow(driver, config, menu_context)
    if not ok:
        return False, f"[no_water_supply_1] Bootstrap failed: {err}"

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
        return False, f"[no_water_supply_1] DB/service error: {exc}"

    if not reasons:
        return False, "[no_water_supply_1] No outage reasons found in SUPPLY_OUTAGE_REASONS config."

    first_reason = reasons[0]
    print(
        f"[no_water_supply_1] {len(reasons)} outage reason(s) loaded. "
        f"Will select reason 1: {first_reason.get('name')!r}"
    )

    # ------------------------------------------------------------------
    # Step 3: Identify "Report Issue" option number in main menu
    # ------------------------------------------------------------------
    report_issue_number = _find_option_by_label(
        main_menu["item_selection"]["options"], REPORT_ISSUE_LABEL, lang_symbol
    )
    if report_issue_number is None:
        return False, (
            f"[no_water_supply_1] Could not find 'Report Issue' option in main menu.\n"
            f"  Labels tried: {REPORT_ISSUE_LABEL}"
        )
    print(f"[no_water_supply_1] 'Report Issue' option number: {report_issue_number}")

    # ------------------------------------------------------------------
    # Step 4: Send "Report Issue" option, receive issue-type sub-menu
    # ------------------------------------------------------------------
    try:
        report_issue_reply = send_message(driver, report_issue_number, config.response_timeout)
        print(f"[no_water_supply_1] Report Issue reply: {report_issue_reply}")
    except Exception as exc:
        return False, f"[no_water_supply_1] Error sending 'Report Issue' option: {exc}"

    # ------------------------------------------------------------------
    # Step 5: Identify "No Water Supply" option in sub-menu reply
    # ------------------------------------------------------------------
    no_water_number = _find_option_in_reply(
        report_issue_reply, NO_WATER_SUPPLY_LABEL, lang_symbol
    )
    if no_water_number is None:
        return False, (
            f"[no_water_supply_1] Could not find 'No Water Supply' option in reply.\n"
            f"  Labels tried: {NO_WATER_SUPPLY_LABEL}\n"
            f"  Reply: {report_issue_reply!r}"
        )
    print(f"[no_water_supply_1] 'No Water Supply' option number: {no_water_number}")

    # ------------------------------------------------------------------
    # Step 6: Send "No Water Supply" option, receive outage-reason list
    # ------------------------------------------------------------------
    try:
        reasons_reply = send_message(driver, no_water_number, config.response_timeout)
        print(f"[no_water_supply_1] Outage reasons reply: {reasons_reply}")
    except Exception as exc:
        return False, f"[no_water_supply_1] Error sending 'No Water Supply' option: {exc}"

    # ------------------------------------------------------------------
    # Step 7: Validate outage reasons prompt
    # ------------------------------------------------------------------
    passed, message = validate_outage_reasons_prompt(reasons_reply, reasons)
    if not passed:
        return False, f"[no_water_supply_1] Outage reasons prompt validation failed: {message}"
    print("[no_water_supply_1] Outage reasons prompt validation: PASSED")

    # ------------------------------------------------------------------
    # Step 8: Capture IST timestamp, then send reason option "1"
    # The timestamp is captured just before sending so that the analytics
    # DB filter (created_at > sent_at) reliably excludes any pre-existing rows.
    # ------------------------------------------------------------------
    sent_at = datetime.now(tz=IST)
    print(f"[no_water_supply_1] Sending reason '1' at {sent_at.isoformat()}")

    try:
        confirmation_reply = send_message(driver, "1", config.response_timeout)
        print(f"[no_water_supply_1] Confirmation reply: {confirmation_reply}")
    except Exception as exc:
        return False, f"[no_water_supply_1] Error sending reason option '1': {exc}"

    # The bot sends two replies in sequence:
    #   [1] Confirmation message
    #   [2] The main menu again
    # Wait for [2] so the next flow starts with a clean conversation state.
    post_confirmation_menu = wait_for_nth_reply(driver, 2, config.response_timeout)
    print(f"[no_water_supply_1] Post-confirmation main menu: {post_confirmation_menu}")

    # ------------------------------------------------------------------
    # Step 9 & 10: Verify anomaly record in analytics DB
    # ------------------------------------------------------------------
    try:
        analytics_conn = get_analytics_connection()
        try:
            passed, message = validate_anomaly_record(
                analytics_conn, ANOMALY_USER_ID, ANOMALY_SCHEME_ID, sent_at
            )
        finally:
            analytics_conn.close()
    except Exception as exc:
        return False, f"[no_water_supply_1] Analytics DB error: {exc}"

    if not passed:
        return False, f"[no_water_supply_1] Anomaly record validation failed: {message}"

    print("[no_water_supply_1] Anomaly record validation: PASSED")
    return True, ""
