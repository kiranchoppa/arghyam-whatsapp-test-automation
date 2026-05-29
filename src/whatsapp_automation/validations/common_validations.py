"""Validation functions shared across all flows.

Every validation function returns a ``(passed: bool, message: str)`` tuple.
- On success : ``(True, "")``
- On failure : ``(False, "<reason>")``

Callers decide how to handle the result; no exception is ever raised.
"""


def validate_main_menu(response: str, main_menu: dict) -> tuple[bool, str]:
    """Check that *response* contains the expected ITEM_SELECTION main menu.

    Checks:
    - The prompt text is present in the response.
    - Every option label is present in the response.

    Args:
        response:   The raw text received from WhatsApp (may include a
                    trailing timestamp line such as "9:19 pm").
        main_menu:  A dict as returned by
                    ``select_channel_service.get_main_menu()``,
                    with keys ``"item_selection"`` (dict) and
                    ``"lang_symbol"`` (str).

    Returns:
        ``(True, "")`` if all checks pass, otherwise
        ``(False, "<reason>")`` describing the first failed check.
    """
    item_selection = main_menu["item_selection"]
    lang_symbol = main_menu["lang_symbol"]

    prompt = item_selection["prompt"][lang_symbol]
    if prompt not in response:
        return False, (
            f"Main menu prompt not found in response.\n"
            f"  Expected : {prompt!r}\n"
            f"  Response : {response!r}"
        )

    for option in item_selection["options"].values():
        label = option["label"][lang_symbol]
        if label not in response:
            return False, (
                f"Main menu option not found in response.\n"
                f"  Expected option : {label!r}\n"
                f"  Response        : {response!r}"
            )

    return True, ""
