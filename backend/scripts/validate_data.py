"""Validate the raw store without writing processed files: checksums, schema drift, quality counts.

    python -m scripts.validate_data
Exit code 1 if any raw file fails its checksum or a run lacks canonical fields.
"""

from __future__ import annotations

import json
import sys

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.pipeline import market_processing, raw_store


def main() -> int:
    configure_logging()
    failed = False
    runs = raw_store.list_runs(market_processing.DATASET)
    if not runs:
        print("No AGMARKNET raw runs. Fetch data first (scripts.fetch_official_data).")
        return 0
    frame, raw_report = market_processing.load_raw_frame(runs, get_settings().market_state_list)
    if raw_report["integrity_failures"]:
        failed = True
        print("INTEGRITY FAILURES:", json.dumps(raw_report["integrity_failures"], indent=2))
    for run_id, info in raw_report["runs"].items():
        if info["missing_canonical_fields"]:
            failed = True
            print(f"SCHEMA: run {run_id} missing {info['missing_canonical_fields']}")
        if info.get("complete") is False:
            print(f"WARNING: run {run_id} incomplete ({info['record_count']}/{info['total_reported_by_api']})")
    _, report = market_processing.validate_and_clean(frame)
    print(json.dumps({k: v for k, v in report.items() if k != "markets_in_multiple_districts"}, indent=2, default=str))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
