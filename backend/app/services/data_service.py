"""Read-only access to processed Parquet files and source metadata (reloaded when files change)."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any

import pandas as pd

from app.core.config import get_settings
from app.core.exceptions import DataUnavailableError

_cache: dict[Path, tuple[float, pd.DataFrame]] = {}
_lock = Lock()


def _read_parquet(path: Path, hint: str) -> pd.DataFrame:
    if not path.exists():
        raise DataUnavailableError(f"{path.name} has not been generated yet. {hint}")
    mtime = path.stat().st_mtime
    with _lock:
        hit = _cache.get(path)
        if hit and hit[0] == mtime:
            return hit[1]
        df = pd.read_parquet(path)
        _cache[path] = (mtime, df)
        return df


def market_prices() -> pd.DataFrame:
    df = _read_parquet(
        get_settings().market_prices_path,
        "Import an official AGMARKNET CSV (scripts.fetch_official_data market-import) and run `python -m scripts.preprocess_data`.",
    )
    return df


def crop_production() -> pd.DataFrame:
    return _read_parquet(
        get_settings().crop_production_path,
        "Import the official crop production CSV (scripts.fetch_official_data crop-import) and run `python -m scripts.preprocess_data`.",
    )


def read_metadata_file(name: str) -> dict[str, Any] | None:
    path = get_settings().metadata_dir / name
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def sources() -> list[dict[str, Any]]:
    data = read_metadata_file("sources.json")
    return (data or {}).get("sources", [])


def source_for(dataset: str) -> dict[str, Any] | None:
    """Summary provenance for a processed dataset, used in API responses."""
    for s in sources():
        if s.get("dataset") == dataset and s.get("processed_file"):
            return s
    return None
