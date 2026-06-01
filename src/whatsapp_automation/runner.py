"""Top-level automation runners."""

import sys
from datetime import datetime
from typing import List, Optional

from selenium.common.exceptions import WebDriverException

from whatsapp_automation.config import load_config
from whatsapp_automation.create_report import write_report
from whatsapp_automation.driver_factory import create_driver
from whatsapp_automation.flows.flow_registry import FLOW_REGISTRY
from whatsapp_automation.messaging import close_whatsapp, open_whatsapp, send_message


def _run_default(driver, config):
    """Original single send-and-read flow (no flow key supplied)."""
    print(f"Browser  : {config.browser}")
    print(f"To       : {config.recipient_number}")
    print(f"Send timeout     : {config.send_timeout}s")
    print(f"Response timeout : {config.response_timeout}s")

    open_whatsapp(driver, config.recipient_number, config.send_timeout)
    response_message = send_message(driver, config.start_message, config.response_timeout)
    print("Message sent!")
    print("\nLatest incoming message:")
    print(response_message)


def run_whatsapp_automation(flows: Optional[List[str]] = None):
    """Run automation with an optional list of named flow tests.

    Args:
        flows: A list of flow keys defined in ``flow_registry.FLOW_REGISTRY``.
               Each key maps to a module with a ``run(driver, config)``
               function that returns ``(passed: bool, error_message: str)``.
               Flows execute in the order given, sharing one browser session.
               When *flows* is ``None`` or empty the original default
               send-and-read behaviour is used instead.

    Returns:
        0 if all flows passed (or default mode ran), 1 if any flow failed,
        2 on a startup error (browser or config).
    """
    driver = None
    config = None
    try:
        config = load_config()
        driver = create_driver(
            browser=config.browser,
            edge_profile_dir=config.edge_profile_dir,
            edge_profile_name=config.edge_profile_name,
            keep_browser_open=config.keep_browser_open,
        )

        if not flows:
            _run_default(driver, config)
            return 0

        # Validate all keys up-front so we fail fast before touching the browser.
        unknown = [key for key in flows if key not in FLOW_REGISTRY]
        if unknown:
            raise ValueError(
                f"Unknown flow key(s): {unknown}. "
                f"Available keys: {list(FLOW_REGISTRY.keys())}"
            )

        run_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        open_whatsapp(driver, config.recipient_number, config.send_timeout)

        results = []
        passed_count = 0
        failed_count = 0

        for key in flows:
            print(f"\n--- Running flow: {key} ---")
            try:
                ok, err_msg = FLOW_REGISTRY[key].run(driver, config)
            except Exception as exc:
                ok, err_msg = False, str(exc)

            if ok:
                passed_count += 1
                results.append({"flow_name": key, "status": "PASS", "error_message": "-"})
                print(f"--- Flow {key}: PASS ---")
            else:
                failed_count += 1
                results.append({"flow_name": key, "status": "FAIL", "error_message": err_msg})
                print(f"--- Flow {key}: FAIL — {err_msg} ---")

        print(f"\n=== Results: {passed_count} passed, {failed_count} failed ===")
        write_report(results, run_timestamp)

        return 0 if failed_count == 0 else 1

    except WebDriverException as exc:
        print(
            "Could not start browser session. Close existing Edge windows using the same "
            "profile and retry.",
            file=sys.stderr,
        )
        print(str(exc), file=sys.stderr)
        return 2
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    finally:
        if driver and not (config and config.keep_browser_open):
            close_whatsapp(driver)
