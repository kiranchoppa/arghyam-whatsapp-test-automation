"""Pre-run flow validation.

Validates whether registered flows are applicable given the current DB state,
returns pre-built result entries for flows that must be skipped, and produces
a ``menu_context`` dict that tells bootstrap_flow which conditional main-menu
options are legitimately absent for this tenant.
"""

from whatsapp_automation.flows.flow_registry import FLOW_CATEGORIES
from whatsapp_automation.services.select_channel_service import get_channel_config
from whatsapp_automation.services.select_language_service import get_language_list

_CHANNEL_SKIP_MESSAGE = "Number of channels present is 1; this flow is not applicable."
_CHANNEL_HIDDEN_FLOW_KEY = "select_channel_hidden"
_CHANNEL_HIDDEN_SKIP_MESSAGE = "Channels > 1; select_channel_hidden is not applicable."

_LANGUAGE_SKIP_MESSAGE = "Number of languages present is 1; this flow is not applicable."
_LANGUAGE_HIDDEN_FLOW_KEY = "select_language_hidden"
_LANGUAGE_HIDDEN_SKIP_MESSAGE = "Languages > 1; select_language_hidden is not applicable."

# Keep legacy aliases so any external callers are unaffected.
_SKIP_MESSAGE = _CHANNEL_SKIP_MESSAGE
_HIDDEN_FLOW_KEY = _CHANNEL_HIDDEN_FLOW_KEY
_HIDDEN_SKIP_MESSAGE = _CHANNEL_HIDDEN_SKIP_MESSAGE


def _validate_channel_flows(
    flows: list[str], channels: list
) -> tuple[list[str], list[dict]]:
    """Apply channel-count gating for the ``select_channel`` category.

    Uses the pre-fetched *channels* list so no extra DB call is needed.
    """
    select_channel_keys = set(FLOW_CATEGORIES.get("select_channel", {}).keys())
    requested_select_channel = [f for f in flows if f in select_channel_keys]

    if not requested_select_channel:
        return flows, []

    if len(channels) > 1:
        if _CHANNEL_HIDDEN_FLOW_KEY in flows:
            skipped_results = [
                {
                    "flow_name": _CHANNEL_HIDDEN_FLOW_KEY,
                    "status": "PASS",
                    "error_message": _CHANNEL_HIDDEN_SKIP_MESSAGE,
                }
            ]
            remaining_flows = [f for f in flows if f != _CHANNEL_HIDDEN_FLOW_KEY]
            return remaining_flows, skipped_results
        return flows, []

    print(
        f"[flow_validations] Only {len(channels)} channel(s) configured "
        f"({channels}). Skipping select_channel flows: "
        f"{[f for f in requested_select_channel if f != _CHANNEL_HIDDEN_FLOW_KEY]}"
    )

    skipped_results = [
        {
            "flow_name": key,
            "status": "PASS",
            "error_message": _CHANNEL_SKIP_MESSAGE,
        }
        for key in flows
        if key in select_channel_keys and key != _CHANNEL_HIDDEN_FLOW_KEY
    ]

    remaining_flows = [
        f for f in flows if f not in select_channel_keys or f == _CHANNEL_HIDDEN_FLOW_KEY
    ]
    if _CHANNEL_HIDDEN_FLOW_KEY not in remaining_flows:
        remaining_flows = [_CHANNEL_HIDDEN_FLOW_KEY] + remaining_flows

    return remaining_flows, skipped_results


def _validate_language_flows(
    flows: list[str], languages: list
) -> tuple[list[str], list[dict]]:
    """Apply language-count gating for the ``select_language`` category.

    Uses the pre-fetched *languages* list so no extra DB call is needed.
    """
    select_language_keys = set(FLOW_CATEGORIES.get("select_language", {}).keys())
    requested_select_language = [f for f in flows if f in select_language_keys]

    if not requested_select_language:
        return flows, []

    if len(languages) > 1:
        if _LANGUAGE_HIDDEN_FLOW_KEY in flows:
            skipped_results = [
                {
                    "flow_name": _LANGUAGE_HIDDEN_FLOW_KEY,
                    "status": "PASS",
                    "error_message": _LANGUAGE_HIDDEN_SKIP_MESSAGE,
                }
            ]
            remaining_flows = [f for f in flows if f != _LANGUAGE_HIDDEN_FLOW_KEY]
            return remaining_flows, skipped_results
        return flows, []

    print(
        f"[flow_validations] Only {len(languages)} language(s) configured "
        f"({languages}). Skipping select_language flows: "
        f"{[f for f in requested_select_language if f != _LANGUAGE_HIDDEN_FLOW_KEY]}"
    )

    skipped_results = [
        {
            "flow_name": key,
            "status": "PASS",
            "error_message": _LANGUAGE_SKIP_MESSAGE,
        }
        for key in flows
        if key in select_language_keys and key != _LANGUAGE_HIDDEN_FLOW_KEY
    ]

    remaining_flows = [
        f for f in flows if f not in select_language_keys or f == _LANGUAGE_HIDDEN_FLOW_KEY
    ]
    if _LANGUAGE_HIDDEN_FLOW_KEY not in remaining_flows:
        remaining_flows = [_LANGUAGE_HIDDEN_FLOW_KEY] + remaining_flows

    return remaining_flows, skipped_results


def validate_flows(
    connection, flows: list[str]
) -> tuple[list[str], list[dict], dict]:
    """Validate whether each flow in *flows* can run given the current DB state.

    Always fetches channel count and language count regardless of which flows
    are requested, so that ``menu_context`` accurately reflects which
    conditional main-menu options are visible for this tenant.

    Flow-gating (skip/inject rules) is applied only for flows that appear in
    the requested *flows* list — unchanged behaviour from before.

    Args:
        connection: Open psycopg2 connection; caller manages lifecycle.
        flows:      Ordered list of flow keys to be executed.

    Returns:
        A 3-tuple ``(remaining_flows, skipped_results, menu_context)`` where:

        - ``remaining_flows`` — flow keys that should still be executed.
        - ``skipped_results`` — list of result dicts ready for ``write_report``,
          one per skipped flow, each with ``status="PASS"`` and an explanatory
          ``error_message``.
        - ``menu_context`` — dict with visibility flags for conditional main-menu
          options, e.g.::

              {
                  "select_channel_visible": True,
                  "select_language_visible": False,
              }

          ``bootstrap_flow`` uses this to skip validation of options that are
          legitimately absent from the bot's main-menu reply.
    """
    # Always fetch both counts — needed for menu_context even if the
    # corresponding flow categories were not requested.
    channel_config = get_channel_config(connection)
    channels = channel_config.get("channels", [])
    languages = get_language_list(connection)

    menu_context = {
        "select_channel_visible": len(channels) > 1,
        "select_language_visible": len(languages) > 1,
    }

    all_skipped: list[dict] = []

    flows, channel_skipped = _validate_channel_flows(flows, channels)
    all_skipped.extend(channel_skipped)

    flows, language_skipped = _validate_language_flows(flows, languages)
    all_skipped.extend(language_skipped)

    return flows, all_skipped, menu_context
