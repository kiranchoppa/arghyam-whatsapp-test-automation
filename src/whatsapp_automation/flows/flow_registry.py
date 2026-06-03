"""Flow registry — maps keyword strings to flow runner callables.

Each value must be a module that exposes a ``run(driver, config)`` function.

To add a new flow test:
  1. Create a new .py file inside the appropriate folder under ``flows/``.
  2. Implement ``def run(driver, config): ...`` inside that file.
  3. Import the module here, add its keyword to the relevant category in
     ``FLOW_CATEGORIES``, and ``FLOW_REGISTRY`` will be derived automatically.

Usage in send_whatsapp.py:
    run_whatsapp_automation(flows=["select_channel_1", "select_language_1"])
"""

from whatsapp_automation.flows.no_water_supply import (
    no_water_supply_1,
    no_water_supply_2,
    no_water_supply_3,
)
from whatsapp_automation.flows.select_channel import (
    select_channel_1,
    select_channel_2,
    select_channel_3,
    select_channel_hidden,
)
from whatsapp_automation.flows.select_language import (
    select_language_1,
    select_language_2,
    select_language_hidden,
)

FLOW_CATEGORIES: dict[str, dict[str, object]] = {
    "select_channel": {
        "select_channel_1": select_channel_1,
        "select_channel_2": select_channel_2,
        "select_channel_3": select_channel_3,
        "select_channel_hidden": select_channel_hidden,
    },
    "select_language": {
        "select_language_1": select_language_1,
        "select_language_2": select_language_2,
        "select_language_hidden": select_language_hidden,
    },
    "no_water_supply": {
        "no_water_supply_1": no_water_supply_1,
        "no_water_supply_2": no_water_supply_2,
        "no_water_supply_3": no_water_supply_3,
    },
}

FLOW_REGISTRY: dict[str, object] = {
    key: module
    for category_flows in FLOW_CATEGORIES.values()
    for key, module in category_flows.items()
}
