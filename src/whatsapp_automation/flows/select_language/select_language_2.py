"""select_language flow — test scenario 2 (cancel confirmation).

Steps
-----
1.  Bootstrap: send start message, validate main menu (DB + WhatsApp).
2.  DB: fetch user's current language preference, language list, and tenant config.
3.  Pick the target language: the first language in the list that is not the
    current preference.  Its 1-based index becomes the option number to send.
4.  Identify the option number associated with "Select Language" in the main menu.
5.  Send that number and receive the language selection prompt.
6.  Validate the language selection prompt and available languages.
7.  Send the target language's option number and receive the "Are you sure?" prompt.
8.  Send "No" to cancel — bot returns to the main menu without updating DB.
9.  Validate the main menu reply and verify the language preference is unchanged.
"""

import re

from whatsapp_automation.db import get_connection
from whatsapp_automation.flows.bootstrap import bootstrap_flow
from whatsapp_automation.messaging import send_message, wait_for_nth_reply
from whatsapp_automation.services.common_service import (
    SELECT_CHANNEL_LABEL,
    SELECT_LANGUAGE_LABEL,
    get_tenant_config,
)
from whatsapp_automation.services.select_language_service import (
    get_language_list,
    get_user_language_preference,
)
from whatsapp_automation.validations.common_validations import validate_main_menu
from whatsapp_automation.validations.select_language_validations import (
    validate_language_preference,
    validate_language_selection_prompt,
)


def _find_option_number(options: dict, lang_symbol: str) -> str | None:
    """Return the option number whose label matches the "Select Language" label for *lang_symbol*.

    Performs a case-insensitive substring match against the localised label so
    minor punctuation or spacing differences in the config do not cause misses.

    Args:
        options:     The ``options`` dict from the ITEM_SELECTION screen,
                     keyed by option number strings (e.g. ``{"1": {...}, "2": {...}}``).
        lang_symbol: The ISO language symbol resolved for the user (e.g. ``"en"`` or ``"hi"``).

    Returns:
        The matching option number string (e.g. ``"2"``), or ``None`` if not found.
    """
    keyword = SELECT_LANGUAGE_LABEL.get(lang_symbol, SELECT_LANGUAGE_LABEL["en"])
    for key, option in options.items():
        label = option.get("label", {}).get(lang_symbol, "")
        if keyword.lower() in label.lower():
            match = re.search(r"\d+$", key)
            return match.group() if match else key
    return None


def run(driver, config, menu_context: dict | None = None) -> tuple[bool, str]:
    """Test scenario 2 for the select_language flow — cancel with "No".

    Returns:
        ``(True, "")`` on full pass, ``(False, reason)`` on any failure.
    """
    # ------------------------------------------------------------------
    # Step 1: Bootstrap — send start message + validate main menu
    # ------------------------------------------------------------------
    ok, err, main_menu = bootstrap_flow(driver, config, menu_context)
    if not ok:
        return False, f"[select_language_2] Bootstrap failed: {err}"

    lang_symbol = main_menu["lang_symbol"]
    item_selection = main_menu["item_selection"]

    # ------------------------------------------------------------------
    # Step 2: DB — fetch current language preference, language list, and
    #         tenant config (single connection for all three queries)
    # ------------------------------------------------------------------
    original_language = None
    languages = None
    tenant_config = None

    try:
        connection = get_connection()
        try:
            original_language = get_user_language_preference(connection, config.user_number)
            languages = get_language_list(connection)
            tenant_config = get_tenant_config(connection)
        finally:
            connection.close()
    except Exception as exc:
        return False, f"[select_language_2] DB/service error: {exc}"

    language_selection = tenant_config["screens"]["LANGUAGE_SELECTION"]

    if not languages:
        return False, "[select_language_2] No active languages found in language list."

    # ------------------------------------------------------------------
    # Step 3: Pick target language — the first in the list that differs
    #         from the current preference.  Compute its 1-based index.
    # ------------------------------------------------------------------
    target_language = None
    language_number = None
    for idx, lang in enumerate(languages, start=1):
        if lang != original_language:
            target_language = lang
            language_number = str(idx)
            break

    if target_language is None:
        return False, (
            f"[select_language_2] No alternative language available. "
            f"Current preference '{original_language}' is the only option."
        )
    print(
        f"[select_language_2] Current preferred language: {original_language!r} "
        f"→ will select {target_language!r} then cancel"
    )

    # ------------------------------------------------------------------
    # Step 4: Identify "Select Language" option number (language-aware)
    # ------------------------------------------------------------------
    select_language_number = _find_option_number(item_selection["options"], lang_symbol)
    if select_language_number is None:
        return False, "[select_language_2] Could not find 'Select Language' option in main menu."
    print(f"[select_language_2] 'Select Language' option number: {select_language_number}")

    # ------------------------------------------------------------------
    # Step 5: Send the "Select Language" option number and receive reply
    # ------------------------------------------------------------------
    try:
        language_reply = send_message(driver, select_language_number, config.response_timeout)
        print(f"[select_language_2] Language selection reply: {language_reply}")
    except Exception as exc:
        return False, f"[select_language_2] Error sending 'Select Language' option: {exc}"

    # ------------------------------------------------------------------
    # Step 6: Validate language selection prompt and available languages
    # ------------------------------------------------------------------
    passed, message = validate_language_selection_prompt(
        language_reply, language_selection, languages, lang_symbol
    )
    if not passed:
        return False, f"[select_language_2] Language selection prompt validation failed: {message}"
    print("[select_language_2] Language selection prompt validation: PASSED")

    # ------------------------------------------------------------------
    # Step 7: Send target language option number — bot replies with
    # "Are you sure?" confirmation prompt.
    # ------------------------------------------------------------------
    try:
        are_you_sure_reply = send_message(driver, language_number, config.response_timeout)
        print(f"[select_language_2] 'Are you sure?' prompt: {are_you_sure_reply}")
    except Exception as exc:
        return False, f"[select_language_2] Error sending language option: {exc}"

    # ------------------------------------------------------------------
    # Step 8: Send "No" to cancel.  The bot does not prompt again; it returns
    # directly to the main menu without updating the DB preference.
    # ------------------------------------------------------------------
    try:
        cancel_reply = send_message(driver, "No", config.response_timeout)
        print(f"[select_language_2] After 'No' reply: {cancel_reply}")
    except Exception as exc:
        return False, f"[select_language_2] Error sending 'No' confirmation: {exc}"

    if not cancel_reply:
        cancel_reply = wait_for_nth_reply(driver, 1, config.response_timeout)
        print(f"[select_language_2] Main menu after 'No' (waited): {cancel_reply}")

    # ------------------------------------------------------------------
    # Step 9: Validate main menu and verify DB language preference unchanged.
    # Re-build hidden_labels from menu_context so conditional options that
    # are absent for this tenant (e.g. "Select Channel" on single-channel
    # tenants) are correctly skipped — same logic as bootstrap_flow.
    # ------------------------------------------------------------------
    ctx = menu_context or {}
    hidden_labels: set[str] = set()
    if not ctx.get("select_channel_visible", True):
        hidden_labels.add(
            SELECT_CHANNEL_LABEL.get(lang_symbol, SELECT_CHANNEL_LABEL["en"])
        )
    if not ctx.get("select_language_visible", True):
        hidden_labels.add(
            SELECT_LANGUAGE_LABEL.get(lang_symbol, SELECT_LANGUAGE_LABEL["en"])
        )

    passed, message = validate_main_menu(cancel_reply, main_menu, hidden_labels)
    if not passed:
        return False, f"[select_language_2] Main menu validation after cancel failed: {message}"
    print("[select_language_2] Main menu validation after cancel: PASSED")

    try:
        connection = get_connection()
        try:
            passed, message = validate_language_preference(
                connection,
                config.user_number,
                original_language,
            )
        finally:
            connection.close()
    except Exception as exc:
        return False, f"[select_language_2] DB error during language preference validation: {exc}"

    if not passed:
        return (
            False,
            f"[select_language_2] Language preference validation failed: {message}",
        )

    print("[select_language_2] Language preference validation: PASSED")
    return True, ""
