"""Market discovery, prices, history, trends and comparisons over official AGMARKNET data."""

from __future__ import annotations

import time
from datetime import date
from threading import Lock
from typing import Any

import pandas as pd

from app.core.config import get_settings
from app.core.exceptions import AppError, NotFoundError
from app.providers import agmarknet
from app.schemas.common import SourceInfo
from app.services import data_service

DATASET = "agmarknet"
SOURCE_NAME = "AGMARKNET mandi prices via Open Government Data Platform India"

_live_cache: dict[tuple, tuple[float, list[dict[str, Any]], dict[str, Any]]] = {}
_live_lock = Lock()


def _filter(df: pd.DataFrame, **eq: str | None) -> pd.DataFrame:
    for col, val in eq.items():
        if val:
            df = df[df[col].fillna("").str.casefold() == val.casefold()]
    return df


def _between(df: pd.DataFrame, start: date | None, end: date | None) -> pd.DataFrame:
    d = pd.to_datetime(df["arrival_date"])
    if start:
        df = df[d >= pd.Timestamp(start)]
        d = pd.to_datetime(df["arrival_date"])
    if end:
        df = df[d <= pd.Timestamp(end)]
    return df


MIRROR_NAME = "AGMARKNET prices via Kaggle mirror (third-party copy of data.gov.in data)"
MIXED_NAME = "AGMARKNET prices: official data.gov.in downloads and a Kaggle mirror"


def local_source(df: pd.DataFrame | None = None) -> SourceInfo:
    """Provenance for locally stored data. Says so explicitly when rows come from a third-party mirror."""
    s = data_service.source_for(DATASET) or {}
    rng = None
    kinds: set[str] = set(s.get("source_kinds") or ["official"])
    if df is not None and len(df):
        rng = [str(df["arrival_date"].min()), str(df["arrival_date"].max())]
        if "source_kind" in df:
            kinds = set(df["source_kind"].dropna().unique()) or kinds
    mirror = "third_party_mirror" in kinds
    name = (MIXED_NAME if "official" in kinds else MIRROR_NAME) if mirror else SOURCE_NAME
    note = "Served from locally stored downloads. Dates are original observation dates."
    if mirror:
        note += (" Some or all rows come from a public Kaggle copy of AGMARKNET data (GODL licence), "
                 "not directly from data.gov.in.")
    return SourceInfo(
        dataset=DATASET,
        name=name,
        publisher=s.get("publisher") or agmarknet.PUBLISHER,
        resource_id=", ".join(s.get("resource_ids", [])) or None,
        resource_url=s.get("resource_url"),
        retrieved_at=s.get("last_retrieved_at"),
        observation_range=rng or s.get("observation_range"),
        live=False,
        cached=True,
        third_party=mirror,
        licence=", ".join(s.get("licences", [])) or None,
        note=note,
    )


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    out = df.copy()
    out["arrival_date"] = out["arrival_date"].astype(str)
    cols = ["state", "district", "market", "commodity", "variety", "grade", "arrival_date",
            "min_price", "max_price", "modal_price", "price_unit"]
    if "source_kind" in out:
        cols.append("source_kind")
    out = out[cols].astype(object).where(out[cols].notna(), None)
    return out.to_dict(orient="records")


# -- discovery --------------------------------------------------------------------------


def states() -> list[str]:
    return sorted(data_service.market_prices()["state"].dropna().unique().tolist())


def districts(state: str) -> list[str]:
    df = _filter(data_service.market_prices(), state=state)
    return sorted(d for d in df["district"].dropna().unique().tolist() if d)


def markets(state: str | None, district: str | None, commodity: str | None) -> list[dict[str, Any]]:
    df = _filter(data_service.market_prices(), state=state, district=district, commodity=commodity)
    g = df.groupby(["state", "district", "market"]).agg(
        observations=("modal_price", "count"), last_observation=("arrival_date", "max")
    )
    g = g.reset_index()
    g["last_observation"] = g["last_observation"].astype(str)
    return g.sort_values(["state", "district", "market"]).to_dict(orient="records")


def commodities(state: str | None, district: str | None, market: str | None) -> list[dict[str, Any]]:
    df = _filter(data_service.market_prices(), state=state, district=district, market=market)
    g = df.groupby("commodity").agg(observations=("modal_price", "count"), markets=("market", "nunique"))
    return g.reset_index().sort_values("commodity").to_dict(orient="records")


def varieties(commodity: str, market: str | None) -> list[dict[str, Any]]:
    df = _filter(data_service.market_prices(), commodity=commodity, market=market)
    if df.empty:
        raise NotFoundError(f"No observations for commodity '{commodity}'.")
    g = df.groupby(["variety", "grade"]).agg(observations=("modal_price", "count"))
    return g.reset_index().to_dict(orient="records")


# -- prices -------------------------------------------------------------------------------


def latest_prices(
    state: str, district: str | None, market: str | None, commodity: str | None, prefer_live: bool = True
) -> tuple[list[dict[str, Any]], SourceInfo, dict[str, Any]]:
    """Today's published prices from data.gov.in; falls back to the latest local observations, labelled cached."""
    settings = get_settings()
    meta: dict[str, Any] = {}
    if prefer_live and settings.has_api_key:
        try:
            records, source = _live_prices(
                {k: v for k, v in {"state": state, "district": district, "market": market,
                                   "commodity": commodity}.items() if v}
            )
            if records:
                return records, source, meta
            meta["live_note"] = "The live resource returned no records for this selection today."
        except AppError as exc:
            meta["live_error"] = {"code": exc.code, "message": exc.message, **exc.details}
    elif prefer_live:
        meta["live_error"] = {"code": "not_configured", "message": "DATA_GOV_API_KEY is not configured."}

    df = _filter(data_service.market_prices(), state=state, district=district, market=market, commodity=commodity)
    if df.empty:
        raise NotFoundError("No official observations exist for this selection in local data.", meta)
    latest = df.sort_values("arrival_date").groupby(
        ["state", "district", "market", "commodity", "variety", "grade"], as_index=False
    ).tail(1)
    return _records(latest.sort_values(["market", "commodity"])), local_source(latest), meta


def _live_prices(filters: dict[str, str]) -> tuple[list[dict[str, Any]], SourceInfo]:
    settings = get_settings()
    key = tuple(sorted(filters.items()))
    with _live_lock:
        hit = _live_cache.get(key)
    if hit and time.time() - hit[0] < settings.live_cache_ttl_seconds:
        records, info = hit[1], hit[2]
    else:
        raw, page = agmarknet.fetch_current_prices(filters, settings=settings)
        records = [
            {**r, "arrival_date": str(r["arrival_date"]) if r["arrival_date"] else None}
            for r in raw
            if r["arrival_date"] is not None and r["modal_price"] is not None and r["modal_price"] > 0
        ]
        info = {
            "publisher": (page.org if page else None) or agmarknet.PUBLISHER,
            "retrieved_at": page.retrieved_at if page else None,
            "excluded_invalid": len(raw) - len(records),
        }
        with _live_lock:
            _live_cache[key] = (time.time(), records, info)
    dates = sorted({r["arrival_date"] for r in records})
    for r in records:
        r.pop("arrival_date_raw", None)
    return records, SourceInfo(
        dataset=DATASET,
        name="AGMARKNET current daily mandi prices (data.gov.in)",
        publisher=info["publisher"],
        resource_id=settings.agmarknet_current_resource_id,
        resource_url=agmarknet.resource_url(settings.agmarknet_current_resource_id),
        retrieved_at=info["retrieved_at"],
        observation_range=[dates[0], dates[-1]] if dates else None,
        live=True,
        cached=False,
        note=f"Fetched from data.gov.in; cached in memory up to {settings.live_cache_ttl_seconds}s. "
        f"{info['excluded_invalid']} invalid rows excluded.",
    )


def history(
    state: str, market: str, commodity: str, district: str | None, variety: str | None,
    grade: str | None, start: date | None, end: date | None,
) -> tuple[list[dict[str, Any]], SourceInfo]:
    df = _filter(data_service.market_prices(), state=state, district=district, market=market,
                 commodity=commodity, variety=variety, grade=grade)
    df = _between(df, start, end).sort_values("arrival_date")
    if df.empty:
        raise NotFoundError("No official observations for this series and date range.")
    return _records(df), local_source(df)


def trends(
    state: str, commodity: str, market: str | None, district: str | None, freq: str,
    start: date | None, end: date | None,
) -> tuple[list[dict[str, Any]], SourceInfo]:
    """Period aggregates of actual observations (no interpolation; empty periods are absent)."""
    df = _filter(data_service.market_prices(), state=state, district=district, market=market, commodity=commodity)
    df = _between(df, start, end)
    if df.empty:
        raise NotFoundError("No official observations for this selection.")
    df = df.assign(period=pd.to_datetime(df["arrival_date"]).dt.to_period(freq).dt.start_time.dt.date.astype(str))
    g = df.groupby("period").agg(
        modal_mean=("modal_price", "mean"),
        modal_median=("modal_price", "median"),
        min_price=("min_price", "min"),
        max_price=("max_price", "max"),
        observations=("modal_price", "count"),
        markets=("market", "nunique"),
    ).reset_index()
    g["modal_mean"] = g["modal_mean"].round(2)
    g = g.astype(object).where(g.notna(), None)
    return g.to_dict(orient="records"), local_source(df)


def compare(state: str, commodity: str, on_date: date | None, district: str | None) -> tuple[list[dict], SourceInfo]:
    """Latest observation per market for one commodity (each row carries its own date)."""
    df = _filter(data_service.market_prices(), state=state, district=district, commodity=commodity)
    if on_date:
        df = df[pd.to_datetime(df["arrival_date"]) <= pd.Timestamp(on_date)]
    if df.empty:
        raise NotFoundError("No official observations to compare for this selection.")
    latest = df.sort_values("arrival_date").groupby(["state", "district", "market"], as_index=False).tail(1)
    return _records(latest.sort_values("modal_price", ascending=False)), local_source(latest)
