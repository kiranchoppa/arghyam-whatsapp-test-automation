"""Validation functions specific to the select_language flow.

Every validation function returns a ``(passed: bool, message: str)`` tuple.
- On success : ``(True, "")``
- On failure : ``(False, "<reason>")``
"""

from whatsapp_automation.services.select_language_service import (
    get_user_language_preference,
)


def validate_language_selection_prompt(
    response: str,
    language_selection: dict,
    languages: list[str],
    lang_symbol: str,
) -> tuple[bool, str]:
    """Check that *response* contains the LANGUAGE_SELECTION prompt and all language options.

    Language option labels are looked up from the ``LANGUAGE_SELECTION`` tenant
    config (keyed by *lang_symbol*) because the bot renders them in the user's
    current language (e.g. ``"अंग्रेज़ी"`` instead of ``"English"`` when the
    current language is Hindi).  If the config provides no ``options`` block,
    the raw DB language names from *languages* are checked as a fallback.

    Args:
        response:           Raw text received from WhatsApp after sending the
                            "select language" option number.
        language_selection: The ``LANGUAGE_SELECTION`` screen block from the
                            tenant config (``config["screens"]["LANGUAGE_SELECTION"]``).
        languages:          List of language names from ``get_language_list``,
                            e.g. ``["English", "Hindi", "Marathi"]``.  Used as
                            a fallback when the config has no ``options`` block.
        lang_symbol:        ISO language symbol resolved for the user (e.g. ``"en"``).

    Returns:
        ``(True, "")`` if all checks pass, otherwise
        ``(False, "<reason>")`` describing the first failed check.
    """
    prompt = language_selection["prompt"][lang_symbol]
    if prompt not in response:
        return False, (
            f"Language selection prompt not found in response.\n"
            f"  Expected : {prompt!r}\n"
            f"  Response : {response!r}"
        )

    options = language_selection.get("options", {})
    if options:
        for option in options.values():
            label = option.get("label", {}).get(lang_symbol, "")
            if label and label not in response:
                return False, (
                    f"Language option label not found in response.\n"
                    f"  Expected label ({lang_symbol!r}) : {label!r}\n"
                    f"  Response                        : {response!r}"
                )
    else:
        for language in languages:
            if language not in response:
                return False, (
                    f"Language option not found in response.\n"
                    f"  Expected language : {language!r}\n"
                    f"  Response          : {response!r}"
                )

    return True, ""


def validate_language_preference(
    connection,
    contact_id: str,
    expected_language: str,
) -> tuple[bool, str]:
    """Verify ``user_language_preference.language_value`` equals *expected_language*.

    Args:
        connection:         Open psycopg2 connection; caller manages lifecycle.
        contact_id:         User phone number passed to ``get_user_language_preference``.
        expected_language:  The language value expected in the DB (e.g. after a
                            successful selection or unchanged after cancel).

    Returns:
        ``(True, "")`` if the DB value matches, otherwise
        ``(False, "<reason>")``.
    """
    try:
        actual_language = get_user_language_preference(connection, contact_id)
    except Exception as exc:
        return False, f"DB check failed while reading user language preference: {exc}"

    if actual_language != expected_language:
        return False, (
            f"DB language preference does not match expected value.\n"
            f"  Expected : {expected_language!r}\n"
            f"  Actual   : {actual_language!r}"
        )

    return True, ""


def validate_language_selection_success(
    response: str,
    language_selection: dict,
    lang_symbol: str,
    connection,
    contact_id: str,
    expected_language: str,
) -> tuple[bool, str]:
    """Check the WhatsApp success reply and verify the DB language preference is updated.

    Two checks are performed in order:
    1. WhatsApp reply contains the expected success message text (from tenant
       config).  If the config has no success_message key the text check is
       skipped and only the DB check runs.
    2. ``user_language_preference.language_value`` for *contact_id* equals
       *expected_language*, confirming the server actually updated the record.

    Args:
        response:           Raw text received from WhatsApp after the "Yes" confirmation.
        language_selection: The ``LANGUAGE_SELECTION`` screen block from the
                            tenant config (``config["screens"]["LANGUAGE_SELECTION"]``).
        lang_symbol:        ISO language symbol resolved for the user (e.g. ``"en"``).
        connection:         Open psycopg2 connection; caller manages lifecycle.
        contact_id:         User phone number passed to ``get_user_language_preference``
                            (with or without leading '+').
        expected_language:  The language name the user just selected (e.g. ``"Hindi"``).

    Returns:
        ``(True, "")`` if all checks pass, otherwise
        ``(False, "<reason>")`` describing the first failed check.
    """
    if not response:
        return False, "No success reply received from WhatsApp after confirmation."

    success_text_by_lang = language_selection.get("success_message") or {}
    success_message = success_text_by_lang.get(lang_symbol)

    if success_message is not None and success_message not in response:
        return False, (
            f"Language selection success message not found in response.\n"
            f"  Expected : {success_message!r}\n"
            f"  Response : {response!r}"
        )

    return validate_language_preference(connection, contact_id, expected_language)
