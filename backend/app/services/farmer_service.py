"""Farmer lots in the cold store and their sale plans across mandis (ADR-026).

Files only: data/farmer/lots.json and data/farmer/settings.json (atomic writes, process lock).
shortcut: single cold-storage facility and a JSON file; move to per-facility files before many sites/users.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any

import pandas as pd

from app.core.config import get_settings
from app.core.exceptions import InputRequiredError, NotFoundError
from app.ml import features as F
from app.ml import predictor
from app.ml.model_loader import get_model
from app.services import data_service, geo
from app.services.storage_planner import scenario

_lock = Lock()
CURRENT_DAYS = 30  # a mandi series counts as current if it has a price within this many days
REQUIRED_SETTINGS = ("storage_state", "storage_district", "transport_per_q_km", "storage_rent_per_q_month",
                     "loss_pct_per_30_days")
DEFAULT_SETTINGS: dict[str, Any] = {
    "storage_state": None, "storage_district": None, "transport_per_q_km": None, "storage_rent_per_q_month": None,
    "loss_pct_per_30_days": None, "market_fee_pct": None, "max_km": None, "km_overrides": {},
}


def _dir() -> Path:
    d = get_settings().data_dir / "farmer"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _read(name: str, default: Any) -> Any:
    p = _dir() / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else json.loads(json.dumps(default))


def _write(name: str, data: Any) -> None:
    p = _dir() / name
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, p)


# --- settings & lots -----------------------------------------------------------------------------
def get_settings_doc() -> dict[str, Any]:
    return {**DEFAULT_SETTINGS, **_read("settings.json", DEFAULT_SETTINGS)}


def update_settings(change: dict[str, Any]) -> dict[str, Any]:
    with _lock:
        s = get_settings_doc()
        for k, v in change.items():
            if k == "km_overrides":
                s["km_overrides"] = {mk: km for mk, km in {**s["km_overrides"], **v}.items() if km is not None}
            elif k in DEFAULT_SETTINGS:
                s[k] = v
        if s["storage_state"] and s["storage_district"] and (s["storage_state"], s["storage_district"]) not in geo.DISTRICT_HQ:
            raise InputRequiredError("Unknown storage district; choose one from the list.", {"field": "storage_district"})
        _write("settings.json", s)
        return s


def list_lots() -> list[dict[str, Any]]:
    return sorted(_read("lots.json", []), key=lambda lot: lot["entry_date"], reverse=True)


def add_lot(lot: dict[str, Any]) -> dict[str, Any]:
    with _lock:
        lots = _read("lots.json", [])
        new = {**lot, "id": uuid.uuid4().hex[:10], "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        lots.append(new)
        _write("lots.json", lots)
        return new


def delete_lot(lot_id: str) -> None:
    with _lock:
        lots = _read("lots.json", [])
        keep = [lot for lot in lots if lot["id"] != lot_id]
        if len(keep) == len(lots):
            raise NotFoundError("No such lot.")
        _write("lots.json", keep)


def get_lot(lot_id: str) -> dict[str, Any]:
    lot = next((x for x in _read("lots.json", []) if x["id"] == lot_id), None)
    if not lot:
        raise NotFoundError("No such lot.")
    return lot


# --- plan ------------------------------------------------------------------------------------------
def _candidate_series(prices: pd.DataFrame, lot: dict[str, Any], today: date) -> list[tuple[str, ...]]:
    """One current series per mandi: the lot's variety/grade if given, else the mandi's most-recorded one."""
    df = prices[prices["commodity"] == lot["commodity"]]
    if lot.get("variety"):
        df = df[df["variety"] == lot["variety"]]
    if lot.get("grade"):
        df = df[df["grade"] == lot["grade"]]
    if df.empty:
        return []
    g = df.groupby(F.SERIES_KEYS)["arrival_date"].agg(["max", "count"]).reset_index()
    g = g[pd.to_datetime(g["max"]) >= pd.Timestamp(today - timedelta(days=CURRENT_DAYS))]
    g = g.sort_values("count", ascending=False).drop_duplicates(["state", "district", "market"])
    return [tuple(str(x) for x in r) for r in g[F.SERIES_KEYS].itertuples(index=False)]


def plan(lot_id: str, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    lot = get_lot(lot_id)
    s = get_settings_doc()
    missing = [k for k in REQUIRED_SETTINGS if s.get(k) is None]
    if missing:
        raise InputRequiredError("Set the cold-storage location and rates in Farmer settings first.", {"fields": missing})
    fee = s["market_fee_pct"] or 0.0
    origin = (s["storage_state"], s["storage_district"])
    days_so_far = max(0, (today - date.fromisoformat(lot["entry_date"])).days)

    prices = data_service.market_prices()
    model = get_model()
    keys = _candidate_series(prices, lot, today)
    forecasts = predictor.forecast_series_batch(prices[prices["commodity"] == lot["commodity"]], keys, model)

    mandis, skipped = [], {"no_forecast": len(keys) - len(forecasts), "too_far": 0}
    for key, fc in forecasts.items():
        series = dict(zip(F.SERIES_KEYS, key))
        mk = f"{series['state']}|{series['district']}|{series['market']}"
        override = s["km_overrides"].get(mk)
        km = override if override is not None else geo.road_km(origin, (series["state"], series["district"]))
        if km is not None and s["max_km"] is not None and km > s["max_km"]:
            skipped["too_far"] += 1
            continue
        latest = fc["latest_observation"]
        common = dict(quantity=lot["quantity_q"], total_cost=None, transport_per_q=(km or 0.0) * s["transport_per_q_km"],
                      fee_pct=fee, storage_per_q_month=s["storage_rent_per_q_month"],
                      loss_pct_per_30=s["loss_pct_per_30_days"])
        options = []
        now = scenario(days=days_so_far, price=latest["modal_price"], low=None, high=None, **common)
        options.append({"sell_after_days": 0, "sell_on": str(today), **now, "price_date": latest["date"]})
        for h in fc["horizons"]:
            if not h["available"]:
                continue
            iv = h["interval"] or {}
            sc = scenario(days=days_so_far + h["horizon_days"], price=h["modal_price"], low=iv.get("lower"),
                          high=iv.get("upper"), **common)
            options.append({"sell_after_days": h["horizon_days"], "sell_on": str(today + timedelta(days=h["horizon_days"])),
                            **sc, "forecast_beats_naive_on_test": h["beats_naive_on_test"]})
        for o in options:
            o["total_selling_cost"] = round(o["transport_cost"] + o["storage_cost"] + o["market_fee"], 2)
        best = max(options, key=lambda o: o["net_revenue"])
        mandis.append({**series, "km": km, "km_source": "override" if override is not None else ("approx" if km is not None else "unknown"),
                       "latest_price_date": latest["date"], "options": options, "best": best})

    mandis.sort(key=lambda m: m["best"]["net_revenue"], reverse=True)
    best_overall = mandis[0] if mandis else None
    sell_now_best = max(mandis, key=lambda m: m["options"][0]["net_revenue"]) if mandis else None
    return {
        "lot": lot,
        "days_in_storage_so_far": days_so_far,
        "settings_used": {k: s[k] for k in (*REQUIRED_SETTINGS, "market_fee_pct", "max_km")},
        "recommendation": None if not best_overall else {
            "state": best_overall["state"], "district": best_overall["district"], "market": best_overall["market"],
            "km": best_overall["km"], **best_overall["best"],
            "gain_vs_best_sell_now": round(best_overall["best"]["net_revenue"] - sell_now_best["options"][0]["net_revenue"], 2),
        },
        "mandis": mandis,
        "skipped": skipped,
        "model_version": model.version,
        "assumptions": [
            "Distances are straight-line between district HQs x 1.3 unless you entered the km for a mandi.",
            "Storage rent and loss are counted from the lot's entry date until the sale day; loss is spread evenly.",
            "Sell-now uses each mandi's latest recorded price; store-later prices are tested forecasts, not guarantees.",
        ],
    }
