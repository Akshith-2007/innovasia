"""Rebuild processed Parquet files, sources.json and quality_report.json from the raw store.

Deterministic: same raw runs -> same processed output. Run from backend/:
    python -m scripts.preprocess_data
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.pipeline import crop_processing, market_processing, raw_store


def _source_entry(dataset: str, runs: list, processed_file: str | None, obs_range: list | None) -> dict[str, Any]:
    return {
        "dataset": dataset,
        "processed_file": processed_file,
        "resource_ids": sorted({m["resource_id"] for _, m in runs if m.get("resource_id")}),
        "resource_url": next((m.get("resource_url") for _, m in runs if m.get("resource_url")), None),
        "source_kinds": sorted({m.get("source_kind") or "official" for _, m in runs}),
        "source_names": sorted({m.get("source_name") for _, m in runs if m.get("source_name")}),
        "licences": sorted({m.get("licence") for _, m in runs if m.get("licence")}),
        "publisher": next((m.get("publisher") for _, m in runs if m.get("publisher")), None),
        "last_retrieved_at": max((m.get("retrieved_at_end") or m.get("retrieved_at_start") or "") for _, m in runs)
        if runs
        else None,
        "observation_range": obs_range,
        "runs": [
            {
                "run_id": m["run_id"],
                "kind": m.get("kind"),
                "source_name": m.get("source_name"),
                "title": m.get("title"),
                "resource_id": m.get("resource_id"),
                "filters": m.get("filters"),
                "source_kind": m.get("source_kind") or "official",
                "upstream_url": m.get("upstream_url"),
                "original_filename": m.get("original_filename"),
                "retrieved_at": m.get("retrieved_at_end") or m.get("retrieved_at_start"),
                "record_count": m.get("record_count"),
                "complete": m.get("complete"),
                "schema_version": m.get("schema_version"),
                "checksums": [p["sha256"] for p in (m.get("pages") or m.get("files") or [])],
            }
            for _, m in runs
        ],
    }


def main() -> int:
    configure_logging()
    s = get_settings()
    s.processed_dir.mkdir(parents=True, exist_ok=True)
    s.metadata_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    quality: dict[str, Any] = {"generated_at": generated_at}
    sources: list[dict[str, Any]] = []

    m_runs = raw_store.list_runs(market_processing.DATASET)
    if m_runs:
        raw_frame, raw_report = market_processing.load_raw_frame(m_runs, s.market_state_list)
        prices, report = market_processing.validate_and_clean(raw_frame)
        report.update(raw_report)
        prices.to_parquet(s.market_prices_path, index=False)
        cov = market_processing.series_coverage(prices)
        report["series_coverage_top"] = cov.head(30).astype(str).to_dict(orient="records")
        quality["market_prices"] = report
        sources.append(_source_entry("agmarknet", m_runs, s.market_prices_path.name, report.get("observation_date_range")))
        print(f"market_prices.parquet: {report['output_records']} rows from {report['input_records']} raw records")
    else:
        print("no AGMARKNET raw runs found; skipping market prices")

    c_runs = raw_store.list_runs(crop_processing.DATASET)
    if c_runs:
        crops, report = crop_processing.process(c_runs)
        crops.to_parquet(s.crop_production_path, index=False)
        quality["crop_production"] = report
        yr = report.get("year_range")
        sources.append(_source_entry("crop_production", c_runs, s.crop_production_path.name,
                                     [str(y) for y in yr] if yr else None))
        print(f"crop_production.parquet: {report['output_records']} rows")
    else:
        print("no crop production raw runs found; skipping")

    (s.metadata_dir / "sources.json").write_text(
        json.dumps({"generated_at": generated_at, "sources": sources}, indent=2, default=str), encoding="utf-8"
    )
    (s.metadata_dir / "quality_report.json").write_text(json.dumps(quality, indent=2, default=str), encoding="utf-8")
    print(f"wrote {s.metadata_dir / 'sources.json'} and quality_report.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
