"""Farmer lots and best-mandi comparison (ADR-026).

An admin records a farmer's lot (location, produce, quantity) and the road distance to each nearby
mandi. For every mandi the storage planner (ADR-023) is run with that mandi's own price series and
transport = distance_km x rate (INR per quintal per km). The option with the highest net receipts wins.
Distances and the fare rate are entered by the admin; nothing is looked up or assumed.

Files only: data/lots/lots.json (atomic replace). shortcut: whole-file rewrite; fine for hundreds of lots.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import AppError, NotFoundError
from app.services import storage_planner

_lock = Lock()


def _path() -> Path:
    d = get_settings().data_dir / "lots"
    d.mkdir(parents=True, exist_ok=True)
    return d / "lots.json"


def _load() -> list[dict[str, Any]]:
    p = _path()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def _save(lots: list[dict[str, Any]]) -> None:
    p = _path()
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(lots, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def list_lots() -> list[dict[str, Any]]:
    return sorted(_load(), key=lambda x: x["created_at"], reverse=True)


def get_lot(lot_id: str) -> dict[str, Any]:
    lot = next((x for x in _load() if x["id"] == lot_id), None)
    if not lot:
        raise NotFoundError(f"No lot with id '{lot_id}'.")
    return lot


def add_lot(data: dict[str, Any]) -> dict[str, Any]:
    lot = {**data, "id": uuid.uuid4().hex[:12], "created_at": datetime.now(timezone.utc).isoformat()}
    with _lock:
        lots = _load()
        lots.append(lot)
        _save(lots)
    return lot


def delete_lot(lot_id: str) -> None:
    with _lock:
        lots = _load()
        kept = [x for x in lots if x["id"] != lot_id]
        if len(kept) == len(lots):
            raise NotFoundError(f"No lot with id '{lot_id}'.")
        _save(kept)


def _options(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Sell-now plus every possible storage scenario of one planner result."""
    out = [{**plan["sell_now"], "days": 0, "label": "Sell now"}]
    for s in plan["scenarios"]:
        if s.get("possible"):
            out.append({**s, "label": f"Store {s['days']} days, then sell"})
    return out


def compare(lot_id: str) -> dict[str, Any]:
    lot = get_lot(lot_id)
    rate = lot["transport_rate_per_quintal_km"]
    rows = []
    for m in lot["mandis"]:
        transport_per_q = round(m["distance_km"] * rate, 2)
        req = {
            "state": m.get("state") or lot["state"], "district": m.get("district"), "market": m["market"],
            "commodity": lot["commodity"], "variety": lot.get("variety"), "grade": lot.get("grade"),
            "quantity_quintals": lot["quantity_quintals"], "total_cost": lot.get("total_cost"),
            "transport_cost_per_quintal": transport_per_q, "market_fee_pct": lot.get("market_fee_pct"),
            "storage_option": lot.get("storage_option") or "sell_now",
            "storage_cost_per_quintal_per_month": lot.get("storage_cost_per_quintal_per_month"),
            "loss_pct_per_30_days": lot.get("loss_pct_per_30_days"),
            "max_storage_days": lot.get("max_storage_days"),
        }
        row: dict[str, Any] = {"market": m["market"], "district": m.get("district"), "distance_km": m["distance_km"],
                               "transport_cost_per_quintal": transport_per_q}
        try:
            plan = storage_planner.plan(req)
        except AppError as e:  # unsupported series, no model, missing input: reported, never filled in
            row.update({"available": False, "error": {"code": e.code, "message": e.message}})
        else:
            opts = _options(plan)
            row.update({
                "available": True, "latest_observation": plan["latest_observation"], "options": opts,
                "best": max(opts, key=lambda o: o["net_revenue"]),
                "model_version": plan["model_version"],
            })
        rows.append(row)

    ok = [r for r in rows if r["available"]]
    best = max(ok, key=lambda r: r["best"]["net_revenue"]) if ok else None
    return {
        "lot": lot,
        "mandis": rows,
        "recommendation": None if not best else {
            "market": best["market"], "distance_km": best["distance_km"], "option": best["best"],
            "margin_over_next_best": _margin(ok, best),
        },
        "assumptions": [
            "Transport = road distance entered by the admin x the fare rate (INR per quintal per km), one way.",
            "Each mandi uses its own latest recorded price and its own trained forecasts; mandis without "
            "enough history get no figure rather than a borrowed one.",
            "Store-later figures are model forecasts with their tested error, not guarantees.",
        ],
    }


def _margin(ok: list[dict[str, Any]], best: dict[str, Any]) -> float | None:
    others = [r["best"]["net_revenue"] for r in ok if r is not best]
    return round(best["best"]["net_revenue"] - max(others), 2) if others else None
