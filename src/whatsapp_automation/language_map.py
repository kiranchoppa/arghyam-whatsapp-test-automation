"""Language name to ISO symbol mapping.

This is a fixed client-side map until language symbols are stored in the DB.
Keys are the full language names returned by user_language_preference.language_value.
Values are the ISO 639-1 codes used as keys inside the tenant config JSON.
"""

LANGUAGE_SYMBOL_MAP = {
    "English": "en",
    "Hindi": "hi",
    "Assamese": "as",
    "Bengali": "bn",
    "Gujarati": "gu",
    "Kannada": "kn",
    "Malayalam": "ml",
    "Marathi": "mr",
    "Odia": "or",
    "Punjabi": "pa",
    "Sanskrit": "sa",
    "Tamil": "ta",
    "Telugu": "te",
    "Urdu": "ur",
}

DEFAULT_LANGUAGE_SYMBOL = "en"


def get_language_symbol(language_name: str) -> str:
    """Return the ISO symbol for *language_name*, falling back to 'en'."""
    return LANGUAGE_SYMBOL_MAP.get(language_name, DEFAULT_LANGUAGE_SYMBOL)
