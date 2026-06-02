"""Pre-run flow validation.

Validates whether registered flows are applicable given the current DB state,
and returns pre-built result entries for flows that must be skipped so they
appear in the CSV report with an informative PASS status.
"""

from whatsapp_automation.flows.flow_registry import FLOW_CATEGORIES
from whatsapp_automation.services.select_channel_service import get_channel_config

_SKIP_MESSAGE = "Number of channels present is 1; this flow is not applicable."
_HIDDEN_FLOW_KEY = "select_channel_hidden"
_HIDDEN_SKIP_MESSAGE = "Channels > 1; select_channel_hidden is not applicable."


def validate_flows(
    connection, flows: list[str]
) -> tuple[list[str], list[dict]]:
    """Validate whether each flow in *flows* can run given the current DB state.

    Enforces two complementary rules for the ``select_channel`` category:

    **Multi-channel rule** — ``select_channel_1/2/3`` require more than one
    channel.  When only one channel is present they are removed from the
    execution list, pre-built as PASS results, and ``select_channel_hidden``
    is automatically injected so the absence of the "Select Channel" option
    in the main menu is verified.

    **Single-channel rule** — ``select_channel_hidden`` is only meaningful
    when exactly one channel is configured.  If it appears in the requested
    flows but channels > 1, it is skipped with an informative PASS result.

    Args:
        connection: Open psycopg2 connection; caller manages lifecycle.
        flows:      Ordered list of flow keys to be executed.

    Returns:
        A tuple ``(remaining_flows, skipped_results)`` where:

        - ``remaining_flows`` — flow keys that should still be executed.
        - ``skipped_results`` — list of result dicts ready for ``write_report``,
          one per skipped flow, each with ``status="PASS"`` and an explanatory
          ``error_message``.
    """
    select_channel_keys = set(FLOW_CATEGORIES.get("select_channel", {}).keys())
    requested_select_channel = [f for f in flows if f in select_channel_keys]

    if not requested_select_channel:
        return flows, []

    channel_config = get_channel_config(connection)
    channels = channel_config.get("channels", [])

    if len(channels) > 1:
        # select_channel_hidden must not run when multiple channels exist.
        if _HIDDEN_FLOW_KEY in flows:
            skipped_results = [
                {
                    "flow_name": _HIDDEN_FLOW_KEY,
                    "status": "PASS",
                    "error_message": _HIDDEN_SKIP_MESSAGE,
                }
            ]
            remaining_flows = [f for f in flows if f != _HIDDEN_FLOW_KEY]
            return remaining_flows, skipped_results
        return flows, []

    # Only one (or zero) channel configured — skip multi-channel flows and
    # inject select_channel_hidden to verify the option is absent from the menu.
    print(
        f"[flow_validations] Only {len(channels)} channel(s) configured "
        f"({channels}). Skipping select_channel flows: "
        f"{[f for f in requested_select_channel if f != _HIDDEN_FLOW_KEY]}"
    )

    skipped_results = [
        {
            "flow_name": key,
            "status": "PASS",
            "error_message": _SKIP_MESSAGE,
        }
        for key in flows
        if key in select_channel_keys and key != _HIDDEN_FLOW_KEY
    ]

    remaining_flows = [f for f in flows if f not in select_channel_keys or f == _HIDDEN_FLOW_KEY]
    if _HIDDEN_FLOW_KEY not in remaining_flows:
        remaining_flows = [_HIDDEN_FLOW_KEY] + remaining_flows

    return remaining_flows, skipped_results
