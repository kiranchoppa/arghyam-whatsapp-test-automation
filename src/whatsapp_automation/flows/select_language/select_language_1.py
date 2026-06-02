"""select_language flow — test scenario 1.

Steps
-----
1.  Bootstrap: send start message, validate main menu (DB + WhatsApp).
    Conditional options like "Select Channel" are skipped automatically when
    the tenant has only one channel (via menu_context from validate_flows).
2.  DB: fetch user's current language preference, language list, and tenant config.
3.  Pick the target language: the first language in the list that is not the
    current preference.  Its 1-based index becomes the option number to send.
4.  Identify the option number associated with "Select Language" in the main menu.
5.  Send that number and receive the language selection prompt.
6.  Validate the language selection prompt and available languages.
7.  Send the target language's option number and receive the "Are you sure?" prompt.
8.  Send "Yes" to confirm and receive the final success reply.
9.  Validate the language selection success message and DB update.
10. Build main menu data for the new language and send the start message again.
11. Validate the main menu reply is now rendered in the newly selected language.
"""

import re

from whatsapp_automation.db import get_connection
from whatsapp_automation.flows.bootstrap import bootstrap_flow
from whatsapp_automation.language_map import get_language_symbol
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
    validate_language_selection_prompt,
    validate_language_selection_success,
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
    """Test scenario 1 for the select_language flow.

    Returns:
        ``(True, "")`` on full pass, ``(False, reason)`` on any failure.
    """
    # ------------------------------------------------------------------
    # Step 1: Bootstrap — send start message + validate main menu.
    # menu_context tells bootstrap_flow which conditional options (e.g.
    # "Select Channel") are absent so they are correctly skipped.
    # ------------------------------------------------------------------
    ok, err, main_menu = bootstrap_flow(driver, config, menu_context)
    if not ok:
        return False, f"[select_language_1] Bootstrap failed: {err}"

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
        return False, f"[select_language_1] DB/service error: {exc}"

    language_selection = tenant_config["screens"]["LANGUAGE_SELECTION"]

    if not languages:
        return False, "[select_language_1] No active languages found in language list."

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
            f"[select_language_1] No alternative language available. "
            f"Current preference '{original_language}' is the only option."
        )
    print(
        f"[select_language_1] Switching from '{original_language}' "
        f"to '{target_language}' (option {language_number})"
    )

    # ------------------------------------------------------------------
    # Step 4: Identify "Select Language" option number (language-aware)
    # ------------------------------------------------------------------
    select_language_number = _find_option_number(item_selection["options"], lang_symbol)
    if select_language_number is None:
        return False, "[select_language_1] Could not find 'Select Language' option in main menu."
    print(f"[select_language_1] 'Select Language' option number: {select_language_number}")

    # ------------------------------------------------------------------
    # Step 5: Send the "Select Language" option number and receive reply
    # ------------------------------------------------------------------
    try:
        language_reply = send_message(driver, select_language_number, config.response_timeout)
        print(f"[select_language_1] Language selection reply: {language_reply}")
    except Exception as exc:
        return False, f"[select_language_1] Error sending 'Select Language' option: {exc}"

    # ------------------------------------------------------------------
    # Step 6: Validate language selection prompt and available languages
    # ------------------------------------------------------------------
    passed, message = validate_language_selection_prompt(
        language_reply, language_selection, languages, lang_symbol
    )
    if not passed:
        return False, f"[select_language_1] Language selection prompt validation failed: {message}"
    print("[select_language_1] Language selection prompt validation: PASSED")

    # ------------------------------------------------------------------
    # Step 7: Send target language option number — bot replies with
    # "Are you sure?" confirmation prompt.
    # ------------------------------------------------------------------
    try:
        are_you_sure_reply = send_message(driver, language_number, config.response_timeout)
        print(f"[select_language_1] 'Are you sure?' prompt: {are_you_sure_reply}")
    except Exception as exc:
        return False, f"[select_language_1] Error sending language option: {exc}"

    # ------------------------------------------------------------------
    # Step 8: Send "Yes" to confirm and receive the final success reply.
    # ------------------------------------------------------------------
    try:
        confirmation_reply = send_message(driver, "Yes", config.response_timeout)
        print(f"[select_language_1] Confirmation reply: {confirmation_reply}")
    except Exception as exc:
        return False, f"[select_language_1] Error sending confirmation: {exc}"

    # ------------------------------------------------------------------
    # Step 8b: Wait for the bot to return to the main menu (second reply
    # after "Yes").  The bot sends two messages in sequence:
    #   [1] "Your preferred language has been set to <language>."
    #   [2] The main menu again (now in the new language)
    # We wait for [2] so the conversation state is clean before the next
    # validation step.
    # ------------------------------------------------------------------
    post_confirmation_menu = wait_for_nth_reply(driver, 2, config.response_timeout)
    print(f"[select_language_1] Post-confirmation main menu: {post_confirmation_menu}")

    # ------------------------------------------------------------------
    # Step 9: Validate success message and verify DB language preference
    # ------------------------------------------------------------------
    try:
        connection = get_connection()
        try:
            passed, message = validate_language_selection_success(
                confirmation_reply,
                language_selection,
                lang_symbol,
                connection,
                config.user_number,
                target_language,
            )
        finally:
            connection.close()
    except Exception as exc:
        return False, f"[select_language_1] DB error during success validation: {exc}"

    if not passed:
        return False, f"[select_language_1] Language selection success validation failed: {message}"
    print("[select_language_1] Language selection success validation: PASSED")

    # ------------------------------------------------------------------
    # Step 10: Build main menu data for the new language.
    # get_language_symbol is a local dict lookup — no DB call needed and
    # it bypasses the stale _cached_language in common_service.
    # ------------------------------------------------------------------
    new_lang_symbol = get_language_symbol(target_language)
    new_main_menu = {
        "item_selection": item_selection,
        "lang_symbol": new_lang_symbol,
    }

    # ------------------------------------------------------------------
    # Step 11: Send start message again and validate the main menu is now
    #          rendered in the newly selected language.
    # ------------------------------------------------------------------
    try:
        new_start_reply = send_message(driver, config.start_message, config.response_timeout)
        print(f"[select_language_1] New start reply (in '{new_lang_symbol}'): {new_start_reply}")
    except Exception as exc:
        return False, f"[select_language_1] Error sending start message for language verification: {exc}"

    # Reuse the same menu_context visibility flags but resolve labels for the
    # new language symbol, since conditional options (e.g. "Select Channel")
    # are equally absent in the new language.
    ctx = menu_context or {}
    new_hidden_labels: set[str] = set()
    if not ctx.get("select_channel_visible", True):
        new_hidden_labels.add(
            SELECT_CHANNEL_LABEL.get(new_lang_symbol, SELECT_CHANNEL_LABEL["en"])
        )
    if not ctx.get("select_language_visible", True):
        new_hidden_labels.add(
            SELECT_LANGUAGE_LABEL.get(new_lang_symbol, SELECT_LANGUAGE_LABEL["en"])
        )

    passed, message = validate_main_menu(new_start_reply, new_main_menu, new_hidden_labels)
    if not passed:
        return False, (
            f"[select_language_1] Main menu not rendered in new language '{new_lang_symbol}': {message}"
        )

    print(
        f"[select_language_1] Main menu in new language '{new_lang_symbol}' validation: PASSED"
    )
    return True, ""
