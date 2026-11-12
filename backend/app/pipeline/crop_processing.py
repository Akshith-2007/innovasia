"""District-wise season-wise crop production statistics -> crop_production.parquet.

Annual district aggregates only. Never interpret as farm-level yield or as daily prices.
"""

from __future__ import annotations

import csv
import io
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from app.pipeline import raw_store
from app.providers.agmarknet import normalise_key

DATASET = "crop_production"

_ALIASES = {
    "state_name": "state",
    "state": "state",
    "district_name": "district",
    "district": "district",
    "crop_year": "year",
    "year": "year",
    "season": "season",
    "crop": "crop",
    "area": "area_ha",
    "area_": "area_ha",
    "area_hectare": "area_ha",
    "production": "production",
    "production_": "production",
    "production_tonnes": "production",
}
COLUMNS = ["state", "district", "year", "season", "crop", "area_ha", "production", "production_unit"]


def _norm(raw: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in raw.items():
        canon = _ALIASES.get(normalise_key(k))
        if canon:
            out[canon] = v
    return out


def _records_from_run(run_dir: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    if manifest.get("kind") == "api":
        return [_norm(r) for r in raw_store.iter_run_records(run_dir, manifest)]
    path = run_dir / manifest["original_filename"]
    text = path.read_bytes().decode("utf-8-sig", errors="replace")
    return [_norm(r) for r in csv.DictReader(io.StringIO(text))]


def process(runs: list[tuple[Path, dict[str, Any]]]) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    integrity: dict[str, list[str]] = {}
    for run_dir, manifest in runs:
        problems = raw_store.verify_run(run_dir, manifest)
        if problems:
            integrity[manifest["run_id"]] = problems
            continue
        for r in _records_from_run(run_dir, manifest):
            r["source_run_id"] = manifest["run_id"]
            rows.append(r)

    report: dict[str, Any] = {"input_records": len(rows), "integrity_failures": integrity}
    if not rows:
        report["output_records"] = 0
        return pd.DataFrame(columns=COLUMNS), report

    df = pd.DataFrame(rows)
    missing_cols = [c for c in ("state", "district", "year", "season", "crop", "area_ha", "production") if c not in df]
    if missing_cols:
        raise ValueError(f"crop production source is missing expected columns: {missing_cols}")

    for c in ("state", "district", "season", "crop"):
        df[c] = df[c].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
    df["year"] = pd.to_numeric(df["year"].astype(str).str.extract(r"(\d{4})")[0], errors="coerce")
    df["area_ha"] = pd.to_numeric(df["area_ha"], errors="coerce")
    df["production"] = pd.to_numeric(df["production"], errors="coerce")

    excluded: Counter[str] = Counter()
    bad_year = df["year"].isna()
    excluded["missing_year"] = int(bad_year.sum())
    df = df[~bad_year]
    neg = (df["area_ha"] < 0) | (df["production"] < 0)
    excluded["negative_area_or_production"] = int(neg.sum())
    df = df[~neg]
    before = len(df)
    df = df.drop_duplicates(subset=["state", "district", "year", "season", "crop", "area_ha", "production"])
    report["exact_duplicates_removed"] = before - len(df)

    # The source publishes coconut production in number of nuts, not tonnes. Keep, but label.
    df["production_unit"] = df["crop"].str.lower().str.contains("coconut").map(
        {True: "nuts (as published)", False: "tonnes"}
    )
    df["year"] = df["year"].astype(int)
    df = df[COLUMNS + ["source_run_id"]].reset_index(drop=True)
    report.update(
        {
            "output_records": int(len(df)),
            "excluded": dict(excluded),
            "missing_production_values_kept_as_null": int(df["production"].isna().sum()),
            "missing_area_values_kept_as_null": int(df["area_ha"].isna().sum()),
            "year_range": [int(df["year"].min()), int(df["year"].max())] if len(df) else None,
            "states": int(df["state"].nunique()),
            "districts": int(df["district"].nunique()),
            "crops": int(df["crop"].nunique()),
        }
    )
    return df, report
