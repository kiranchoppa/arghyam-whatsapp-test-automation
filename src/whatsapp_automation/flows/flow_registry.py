"""Flow registry — maps keyword strings to flow runner callables.

Each value must be a module that exposes a ``run(driver, config)`` function.

To add a new flow test:
  1. Create a new .py file inside the appropriate folder under ``flows/``.
  2. Implement ``def run(driver, config): ...`` inside that file.
  3. Import the module here and add its keyword to ``FLOW_REGISTRY``.

Usage in send_whatsapp.py:
    run_whatsapp_automation(flows=["select_channel_1", "select_channel_2"])
"""

from whatsapp_automation.flows.select_channel import select_channel_1, select_channel_2

FLOW_REGISTRY: dict[str, object] = {
    "select_channel_1": select_channel_1,
    "select_channel_2": select_channel_2,
}
