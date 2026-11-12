"""Raw AGMARKNET runs -> validated, deduplicated market_prices.parquet + quality report.

Rules (see DECISIONS.md ADR-012):
- Records without a parseable arrival date or a positive modal price are excluded and counted.
- Missing prices are never filled. No forward-fill anywhere in this module.
- Suspicious-but-plausible rows are kept and flagged in `quality_flags`; training excludes flagged rows.
- Exact duplicates collapse to one row. Conflicting duplicates keep the most recently retrieved
  publication (later publications may be corrections) and are counted in the report.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from app.pipeline import raw_store
from app.providers.agmarknet import _ALIASES, CANONICAL_FIELDS, PRICE_UNIT, normalise_key, normalise_record

DATASET = "agmarknet"
KEY_COLUMNS = ["state", "district", "market", "commodity", "variety", "grade", "arrival_date"]
PRICE_COLUMNS = ["min_price", "max_price", "modal_price"]
# A modal price more than this multiple away from its series median is flagged as a possible unit error.
OUTLIER_RATIO = 8.0

PROCESSED_COLUMNS = [
    *KEY_COLUMNS,
    *PRICE_COLUMNS,
    "price_unit",
    "quality_flags",
    "source_resource_id",
    "source_run_id",
    "source_kind",
    "retrieved_at",
]


SOURCE_KINDS = ("official", "third_party_mirror")  # later entries lose to earlier ones on conflicts
TEXT_COLUMNS = ["state", "district", "market", "commodity", "variety", "grade"]


def _source_kind(manifest: dict[str, Any]) -> str:
    return manifest.get("source_kind") or "official"


def _load_parquet_run(run_dir: Any, manifest: dict[str, Any], states: list[str] | None) -> tuple[pd.DataFrame, set[str]]:
    """Vectorised path for large columnar imports (e.g. the Kaggle AGMARKNET mirror)."""
    import pyarrow.parquet as pq

    frames = []
    seen: set[str] = set()
    for entry in manifest.get("files", []):
        path = run_dir / entry["file"]
        names = pq.read_schema(path).names
        seen |= {normalise_key(n) for n in names}
        rename = {n: _ALIASES[normalise_key(n)] for n in names if normalise_key(n) in _ALIASES}
        state_col = next((n for n, c in rename.items() if c == "state"), None)
        filters = [(state_col, "in", states)] if states and state_col else None
        df = pd.read_parquet(path, columns=list(rename), filters=filters).rename(columns=rename)
        frames.append(df)
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    for c in TEXT_COLUMNS:
        if c in df:
            df[c] = df[c].astype("string").str.replace(r"\s+", " ", regex=True).str.strip().replace("", pd.NA)
            df[c] = df[c].astype(object).where(df[c].notna(), None)
        else:
            df[c] = None
    raw_dates = df["arrival_date"].astype(str)
    parsed = pd.to_datetime(raw_dates, format="%Y-%m-%d", errors="coerce")
    df["arrival_date"] = [d.date() if not pd.isna(d) else None for d in parsed]
    df["arrival_date_raw"] = raw_dates
    for c in PRICE_COLUMNS:
        df[c] = pd.to_numeric(df.get(c), errors="coerce")
    df["price_unit"] = PRICE_UNIT
    return df, seen


def load_raw_frame(
    runs: list[tuple[Any, dict[str, Any]]], states: list[str] | None = None
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load every intact raw run into canonical columns, optionally restricted to `states`."""
    frames: list[pd.DataFrame] = []
    schema_report: dict[str, Any] = {}
    integrity: dict[str, list[str]] = {}
    wanted = {s.casefold() for s in states} if states else None
    for run_dir, manifest in runs:
        problems = raw_store.verify_run(run_dir, manifest)
        if problems:
            integrity[manifest["run_id"]] = problems
            continue
        files = manifest.get("files") or []
        if manifest.get("kind") == "file_import" and files and all(f["file"].endswith(".parquet") for f in files):
            df, seen_keys = _load_parquet_run(run_dir, manifest, states)
        else:
            seen_keys = {normalise_key(str(f.get("id") or f.get("name"))) for f in manifest.get("fields", [])}
            rows = []
            for rec in raw_store.iter_run_records(run_dir, manifest):
                if not seen_keys:
                    seen_keys = {normalise_key(k) for k in rec}
                row = normalise_record(rec)
                if wanted is None or (row["state"] or "").casefold() in wanted:
                    rows.append(row)
            df = pd.DataFrame(rows)
        df["source_resource_id"] = manifest["resource_id"]
        df["source_run_id"] = manifest["run_id"]
        df["source_kind"] = _source_kind(manifest)
        df["retrieved_at"] = manifest.get("retrieved_at_end") or manifest.get("retrieved_at_start")
        frames.append(df)
        mapped = {_ALIASES.get(k) for k in seen_keys}
        missing = [f for f in CANONICAL_FIELDS if f not in mapped]
        schema_report[manifest["run_id"]] = {
            "resource_id": manifest["resource_id"],
            "source_kind": _source_kind(manifest),
            "fields": sorted(seen_keys),
            "missing_canonical_fields": missing,
            "complete": manifest.get("complete"),
            "total_reported_by_api": manifest.get("total_reported_by_api"),
            "record_count": manifest.get("record_count"),
            "rows_in_scope": int(len(df)),
        }
    frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return frame, {"runs": schema_report, "integrity_failures": integrity, "state_scope": states or "all"}


def validate_and_clean(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    report: dict[str, Any] = {"input_records": int(len(frame))}
    if frame.empty:
        report.update({"output_records": 0, "excluded": {}, "flags": {}})
        return pd.DataFrame(columns=PROCESSED_COLUMNS), report

    excluded: Counter[str] = Counter()
    df = frame.copy()

    # --- hard exclusions -------------------------------------------------------------
    no_date = df["arrival_date"].isna()
    excluded["missing_or_unparseable_arrival_date"] = int(no_date.sum())
    df = df[~no_date]

    for col in ("state", "market", "commodity"):
        missing = df[col].isna()
        excluded[f"missing_{col}"] = int(missing.sum())
        df = df[~missing]

    no_modal = df["modal_price"].isna()
    excluded["missing_or_non_numeric_modal_price"] = int(no_modal.sum())
    df = df[~no_modal]

    nonpos = df["modal_price"] <= 0
    excluded["non_positive_modal_price"] = int(nonpos.sum())
    df = df[~nonpos]

    df["arrival_date"] = pd.to_datetime(df["arrival_date"])
    future = df["arrival_date"] > pd.Timestamp(datetime.now(timezone.utc).date())
    excluded["arrival_date_in_future"] = int(future.sum())
    df = df[~future]

    # --- duplicates ------------------------------------------------------------------
    for col in ("district", "variety", "grade"):
        df[col] = df[col].fillna("")
    before = len(df)
    df = df.drop_duplicates(subset=KEY_COLUMNS + PRICE_COLUMNS)
    exact_dupes = before - len(df)
    # Official publications win over third-party mirrors; within a kind, the latest retrieval wins.
    if "source_kind" not in df:
        df["source_kind"] = "official"
    df["_priority"] = df["source_kind"].map({k: -i for i, k in enumerate(SOURCE_KINDS)}).fillna(-99)
    df = df.sort_values(["_priority", "retrieved_at"], kind="stable").drop(columns="_priority")
    conflicting = df.duplicated(subset=KEY_COLUMNS, keep=False)
    conflicting_groups = int(df[conflicting].groupby(KEY_COLUMNS).ngroups) if conflicting.any() else 0
    df = df.drop_duplicates(subset=KEY_COLUMNS, keep="last")

    # --- soft flags (kept, but excluded from training) --------------------------------
    flags = pd.Series([[] for _ in range(len(df))], index=df.index, dtype=object)

    def flag(mask: pd.Series, name: str) -> int:
        for i in df.index[mask.fillna(False)]:
            flags.at[i].append(name)
        return int(mask.fillna(False).sum())

    flag_counts = {
        "missing_min_price": flag(df["min_price"].isna(), "missing_min_price"),
        "missing_max_price": flag(df["max_price"].isna(), "missing_max_price"),
        "negative_min_or_max": flag((df["min_price"] < 0) | (df["max_price"] < 0), "negative_min_or_max"),
        "min_greater_than_max": flag(df["min_price"] > df["max_price"], "min_greater_than_max"),
        "modal_outside_min_max": flag(
            (df["modal_price"] < df["min_price"]) | (df["modal_price"] > df["max_price"]),
            "modal_outside_min_max",
        ),
    }
    series_median = df.groupby(["state", "district", "market", "commodity", "variety", "grade"])["modal_price"].transform(
        "median"
    )
    ratio = df["modal_price"] / series_median
    flag_counts["possible_unit_error"] = flag(
        (ratio > OUTLIER_RATIO) | (ratio < 1 / OUTLIER_RATIO), "possible_unit_error"
    )
    df["quality_flags"] = flags.map(lambda fl: ";".join(fl))
    df["price_unit"] = PRICE_UNIT

    df = df[PROCESSED_COLUMNS].sort_values(KEY_COLUMNS).reset_index(drop=True)
    df["arrival_date"] = df["arrival_date"].dt.date

    report.update(
        {
            "output_records": int(len(df)),
            "excluded": dict(excluded),
            "exact_duplicates_removed": int(exact_dupes),
            "conflicting_duplicate_groups_resolved_latest_retrieval": conflicting_groups,
            "flags": flag_counts,
            "observation_date_range": [str(df["arrival_date"].min()), str(df["arrival_date"].max())]
            if len(df)
            else None,
            "states": int(df["state"].nunique()),
            "markets": int(df["market"].nunique()),
            "commodities": int(df["commodity"].nunique()),
            "series": int(df.groupby(["state", "district", "market", "commodity", "variety", "grade"]).ngroups),
            "rows_by_source_kind": {str(k): int(v) for k, v in df["source_kind"].value_counts().items()},
            "unknown_commodity_names": sorted(
                c for c in df["commodity"].unique() if not any(ch.isalpha() for ch in c)
            ),
            "markets_in_multiple_districts": _inconsistent_markets(df),
        }
    )
    return df, report


def _inconsistent_markets(df: pd.DataFrame) -> list[dict[str, Any]]:
    g = df.groupby(["state", "market"])["district"].nunique()
    bad = g[g > 1]
    return [{"state": s, "market": m, "districts": int(n)} for (s, m), n in bad.items()][:50]


def series_coverage(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    clean = df[df["quality_flags"] == ""]
    g = clean.groupby(["state", "district", "market", "commodity", "variety", "grade"])["arrival_date"]
    out = g.agg(observations="count", first="min", last="max").reset_index()
    span = (pd.to_datetime(out["last"]) - pd.to_datetime(out["first"])).dt.days + 1
    out["span_days"] = span
    out["density"] = np.round(out["observations"] / span, 3)
    return out.sort_values("observations", ascending=False)
