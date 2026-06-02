"""Pre-run flow validation.

Validates whether registered flows are applicable given the current DB state,
and returns pre-built result entries for flows that must be skipped so they
appear in the CSV report with an informative PASS status.
"""

from whatsapp_automation.flows.flow_registry import FLOW_CATEGORIES
from whatsapp_automation.services.select_channel_service import get_channel_config

_SKIP_MESSAGE = "Number of channels present is 1; this flow is not applicable."


def validate_flows(
    connection, flows: list[str]
) -> tuple[list[str], list[dict]]:
    """Validate whether each flow in *flows* can run given the current DB state.

    Currently enforces one rule:

    **select_channel rule** — all flows in the ``select_channel`` category
    require more than one channel to be configured for the tenant.  When only
    one channel is present the flows are removed from the execution list and a
    PASS result is pre-built for each of them so they appear in the report.

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
        return flows, []

    print(
        f"[flow_validations] Only {len(channels)} channel(s) configured "
        f"({channels}). Skipping select_channel flows: {requested_select_channel}"
    )

    skipped_results = [
        {
            "flow_name": key,
            "status": "PASS",
            "error_message": _SKIP_MESSAGE,
        }
        for key in flows
        if key in select_channel_keys
    ]

    remaining_flows = [f for f in flows if f not in select_channel_keys]
    return remaining_flows, skipped_results
