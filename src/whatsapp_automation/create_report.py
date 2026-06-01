"""CSV report generation for automation run results."""

import csv
from pathlib import Path


_REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"


def write_report(results: list[dict], timestamp: str) -> None:
    """Write a CSV report to ``reports/<timestamp>.csv``.

    Creates the ``reports/`` directory next to ``src/`` if it does not exist.

    Args:
        results:   List of result dicts, each with keys:
                   - ``flow_name`` (str): registered key of the flow.
                   - ``status``    (str): ``"PASS"`` or ``"FAIL"``.
                   - ``error_message`` (str): failure reason, or ``"-"`` on pass.
        timestamp: Run-start timestamp string formatted as
                   ``YYYY-MM-DD_HH-MM-SS`` (supplied by the runner).

    The CSV columns are: ``flow_name``, ``status``, ``error_message``.
    """
    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filepath = _REPORTS_DIR / f"{timestamp}.csv"

    with filepath.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["flow_name", "status", "error_message"])
        writer.writeheader()
        for row in results:
            writer.writerow({
                "flow_name": row["flow_name"],
                "status": row["status"],
                "error_message": row["error_message"] if row["status"] == "FAIL" else "-",
            })

    print(f"\nReport written to: {filepath}")
