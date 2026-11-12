"""Descriptive district crop statistics. District annual aggregates only — not farm-level yield."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.core.exceptions import NotFoundError
from app.schemas.common import SourceInfo
from app.services import data_service

DATASET = "crop_production"
YIELD_NOTE = (
    "Yield = district production / district area for the season (annual aggregate). "
    "It is not a farm-level measurement or prediction."
)


def _filter(df: pd.DataFrame, **eq: str | None) -> pd.DataFrame:
    for col, val in eq.items():
        if val:
            df = df[df[col].str.casefold() == val.casefold()]
    return df


def source(df: pd.DataFrame | None = None) -> SourceInfo:
    s = data_service.source_for(DATASET) or {}
    rng = [str(int(df["year"].min())), str(int(df["year"].max()))] if df is not None and len(df) else None
    return SourceInfo(
        dataset=DATASET,
        name="District-wise, season-wise crop production statistics (data.gov.in)",
        publisher=s.get("publisher"),
        resource_id=", ".join(s.get("resource_ids", [])) or None,
        resource_url=s.get("resource_url"),
        retrieved_at=s.get("last_retrieved_at"),
        observation_range=rng,
        live=False,
        cached=True,
        note="Annual district aggregates. Years are crop years as published.",
    )


def _clean(g: pd.DataFrame) -> list[dict[str, Any]]:
    return g.astype(object).where(g.notna(), None).to_dict(orient="records")


def production(state: str, crop: str, district: str | None, season: str | None) -> tuple[list[dict], SourceInfo]:
    df = _filter(data_service.crop_production(), state=state, crop=crop, district=district, season=season)
    if df.empty:
        raise NotFoundError("No production statistics for this selection.")
    g = df.groupby(["year", "production_unit"], as_index=False).agg(
        area_ha=("area_ha", lambda s: s.sum(min_count=1)),
        production=("production", lambda s: s.sum(min_count=1)),
        districts=("district", "nunique"),
    )
    return _clean(g.sort_values("year")), source(df)


def yield_series(state: str, crop: str, district: str | None) -> tuple[list[dict], SourceInfo]:
    rows, src = production(state, crop, district, None)
    for r in rows:
        area, prod = r["area_ha"], r["production"]
        r["yield_per_ha"] = round(prod / area, 3) if area and prod is not None and area > 0 else None
    return rows, src


def district_comparison(state: str, crop: str, year: int | None) -> tuple[list[dict], SourceInfo, int]:
    df = _filter(data_service.crop_production(), state=state, crop=crop)
    if df.empty:
        raise NotFoundError("No production statistics for this selection.")
    year = year or int(df["year"].max())
    df = df[df["year"] == year]
    if df.empty:
        raise NotFoundError(f"No production statistics for {year}.")
    g = df.groupby(["district", "production_unit"], as_index=False).agg(
        area_ha=("area_ha", lambda s: s.sum(min_count=1)),
        production=("production", lambda s: s.sum(min_count=1)),
    )
    g["yield_per_ha"] = (g["production"] / g["area_ha"].where(g["area_ha"] > 0)).round(3)
    return _clean(g.sort_values("production", ascending=False)), source(df), year


def options() -> dict[str, Any]:
    df = data_service.crop_production()
    return {
        "states": sorted(df["state"].unique().tolist()),
        "crops": sorted(df["crop"].unique().tolist()),
        "seasons": sorted(df["season"].unique().tolist()),
        "years": [int(df["year"].min()), int(df["year"].max())],
    }
