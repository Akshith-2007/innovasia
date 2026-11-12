"""Sell-now vs store-and-sell-later planner (ADR-023).

Defaults come only from cited public sources; where none was found the value is None and the
farmer must enter it. Every number is editable. Forecasts come from the trained horizon models.
"""

from __future__ import annotations

import re
from typing import Any

# --- sources -----------------------------------------------------------------------------------
SRC_CWC = {
    "title": "FCI: CWC storage charges 2019-20 (Rs 5.07 per 50 kg bag per month)",
    "url": "https://www.hrmsfci.in/aps/StorageandContract/IA_Stg_VI_VII/Storage%20charges%202019-20%20CWC%20&%20SWC%20(2).pdf",
    "year": "2019-20",
}
SRC_GUNTUR = {
    "title": "Guntur chilli cold storage: Rs 170-200 per 45-50 kg bag for ~10-month season",
    "url": "https://www.ofbusiness.com/blogs/chilli-sellers-find-new-way-to-trade-during-market-closure/54136",
    "year": "2018-19",
}
SRC_ICAR_ONION = {
    "title": "ICAR: onion storage losses over 120 days (cold storage 0°C: 5%; low-cost ventilated: up to 42%)",
    "url": "https://icar.org.in/node/4701",
    "year": "accessed 2026",
}
SRC_ZECC = {
    "title": "ICAR KRISHI: zero energy cool chamber shelf-life studies (tomato ~14-15 d vs ~7 d; green chilli 6 d vs 2 d)",
    "url": "https://krishi.icar.gov.in/jspui/handle/123456789/39860",
    "year": "study values, approximate",
}

# --- commodity categories ----------------------------------------------------------------------
_CATEGORY_PATTERNS: list[tuple[str, str]] = [
    ("onion", r"\bonion\b"),
    ("potato", r"\bpotato\b"),
    ("dry_chilli", r"dry chill|chilli red|chillies \(red\)|red chill"),
    ("grain_pulse", r"paddy|rice|maize|jowar|bajra|wheat|ragi|gram|arhar|tur\b|moong|urad|lentil|"
                    r"groundnut|soyabean|sunflower|castor|sesam|cotton|turmeric|coriander seed|cumin|"
                    r"horse gram|millet|kulthi|niger"),
    ("perishable", r"tomato|brinjal|bhindi|ladies finger|gourd|beans|cabbage|cauliflower|chilli|capsicum|"
                   r"cucumb|carrot|beetroot|radish|drumstick|leafy|spinach|coriander|methi|pea|"
                   r"mango|banana|papaya|guava|grapes|pomegranate|sapota|watermelon|musk"),
]


def commodity_category(commodity: str) -> str:
    name = commodity.lower()
    for cat, pattern in _CATEGORY_PATTERNS:
        if re.search(pattern, name):
            return cat
    return "other"


# --- catalogue -----------------------------------------------------------------------------------
# cost: INR per quintal per month per category (None = no source, farmer enters it). loss: (percent, over_days) prorated linearly (stated assumption).
# max_days: storable days for the category; None = unknown, farmer must judge.
CATALOG: list[dict[str, Any]] = [
    {
        "id": "sell_now", "name": "Sell now", "suited": ["*"],
        "description": "Sell at the mandi without storing.",
        "cost": {"*": 0.0}, "loss": {"*": (0.0, 1)}, "max_days": {"*": 0}, "sources": [],
    },
    {
        "id": "home_ambient", "name": "Home / shed storage (no cooling)",
        "suited": ["grain_pulse", "dry_chilli", "onion", "perishable", "other"],
        "description": "Bags or heaps kept at home or in a farm shed. No rent, but no temperature control.",
        "cost": {"*": 0.0},
        "loss": {"onion": (42.0, 120)},
        "max_days": {"perishable": 4, "onion": 120},
        "sources": [SRC_ICAR_ONION, SRC_ZECC],
        "notes": "Perishable limit uses room-condition shelf life of brinjal/beans/green chilli (4-5 days).",
    },
    {
        "id": "zecc", "name": "Zero Energy Cool Chamber (ICAR design)", "suited": ["perishable"],
        "description": "Brick-and-sand chamber cooled by evaporating water; cools about 10-14°C. On-farm, no power.",
        "cost": {"*": 0.0},
        "loss": {},
        "max_days": {"perishable": 6},
        "sources": [SRC_ZECC],
        "notes": "Build cost not included. 6 days is the green-chilli figure; tomato reached ~14 days.",
    },
    {
        "id": "onion_ventilated", "name": "Ventilated onion storage structure", "suited": ["onion"],
        "description": "Raised, bottom/side-ventilated structure for bulbs; common for onion in Karnataka and AP.",
        "cost": {"*": 0.0},
        "loss": {"onion": (42.0, 120)},
        "max_days": {"onion": 120},
        "sources": [SRC_ICAR_ONION],
        "notes": "ICAR reports up to 42-46% loss over four months; build cost not included.",
    },
    {
        "id": "cold_storage", "name": "Rented cold storage", "suited": ["dry_chilli", "onion", "potato"],
        "description": "Commercial cold store (e.g. chilli cold storages around Guntur and Khammam).",
        "cost": {"dry_chilli": 40.0},
        "loss": {"onion": (5.0, 120)},
        "max_days": {"dry_chilli": 300, "onion": 120},
        "sources": [SRC_GUNTUR, SRC_ICAR_ONION],
        "notes": "Chilli rent derived from Rs 170-200 per 45-50 kg bag for ~10 months (2018-19). No published rent found for other crops; enter your local quote.",
    },
    {
        "id": "warehouse", "name": "Warehouse / godown (CWC or State Warehousing)",
        "suited": ["grain_pulse", "dry_chilli"],
        "description": "Scientific godown; the receipt can back a pledge loan.",
        "cost": {"grain_pulse": 10.14, "dry_chilli": 10.14},
        "loss": {},
        "max_days": {"grain_pulse": 365, "dry_chilli": 300},
        "sources": [SRC_CWC],
        "notes": "Rs 5.07 per 50 kg bag per month = Rs 10.14 per quintal (2019-20 CWC rate); current rates are higher.",
    },
]


def options_for(commodity: str) -> dict[str, Any]:
    cat = commodity_category(commodity)
    out = []
    for o in CATALOG:
        loss = o["loss"].get(cat) or o["loss"].get("*")
        max_days = o["max_days"].get(cat, o["max_days"].get("*"))
        out.append({
            "id": o["id"], "name": o["name"], "description": o["description"],
            "suited": "*" in o["suited"] or cat in o["suited"],
            "default_cost_per_quintal_per_month": o["cost"].get(cat, o["cost"].get("*")),
            "default_loss_pct_per_30_days": round(loss[0] * 30 / loss[1], 2) if loss else None,
            "default_max_days": max_days,
            "notes": o.get("notes"),
            "sources": o["sources"],
        })
    return {"commodity": commodity, "category": cat, "options": out}


# --- money ---------------------------------------------------------------------------------------
def scenario(
    *, days: int, price: float, low: float | None, high: float | None, quantity: float, total_cost: float | None,
    transport_per_q: float, fee_pct: float, storage_per_q_month: float, loss_pct_per_30: float,
) -> dict[str, Any]:
    """Net money from storing `days` then selling at `price` (INR/quintal). Loss prorated linearly."""
    loss_frac = min(loss_pct_per_30 * days / 30, 100.0) / 100
    sellable = quantity * (1 - loss_frac)
    storage = quantity * storage_per_q_month * days / 30
    transport = quantity * transport_per_q

    def net(p: float) -> float:
        gross = sellable * p
        return gross - gross * fee_pct / 100 - transport - storage

    denom = sellable * (1 - fee_pct / 100)
    return {
        "days": days,
        "price_per_quintal": round(price, 2),
        "sellable_quintals": round(sellable, 3),
        "storage_cost": round(storage, 2),
        "transport_cost": round(transport, 2),
        "market_fee": round(sellable * price * fee_pct / 100, 2),
        "net_revenue": round(net(price), 2),
        "net_revenue_low": round(net(low), 2) if low is not None else None,
        "net_revenue_high": round(net(high), 2) if high is not None else None,
        "profit": round(net(price) - total_cost, 2) if total_cost is not None else None,
        "break_even_price": round((total_cost + transport + storage) / denom, 2)
        if total_cost is not None and denom > 0 else None,
    }


def plan(req: dict[str, Any]) -> dict[str, Any]:
    """Compare selling now with storing for each forecast horizon the chosen storage allows."""
    from app.core.exceptions import InputRequiredError, NotFoundError
    from app.ml import predictor

    opts = {o["id"]: o for o in options_for(req["commodity"])["options"]}
    opt = opts.get(req["storage_option"])
    if not opt:
        raise NotFoundError(f"Unknown storage option '{req['storage_option']}'.", {"options": list(opts)})
    cost = req.get("storage_cost_per_quintal_per_month")
    cost = opt["default_cost_per_quintal_per_month"] if cost is None else cost
    loss = req.get("loss_pct_per_30_days")
    loss = opt["default_loss_pct_per_30_days"] if loss is None else loss
    max_days = req.get("max_storage_days")
    max_days = opt["default_max_days"] if max_days is None else max_days
    if opt["id"] != "sell_now" and cost is None:
        raise InputRequiredError(
            f"No published storage rent for '{opt['name']}' with this commodity. Enter your local rate per quintal per month.",
            {"field": "storage_cost_per_quintal_per_month"},
        )
    if opt["id"] != "sell_now" and loss is None:
        raise InputRequiredError(
            f"No published loss figure for '{opt['name']}' with this commodity. Enter your expected loss % per 30 days.",
            {"field": "loss_pct_per_30_days"},
        )

    query = {k: req.get(k) for k in ("state", "district", "market", "commodity", "variety", "grade")}
    fc = predictor.forecast_horizons(query)
    latest = fc["latest_observation"]["modal_price"]
    common = dict(quantity=req["quantity_quintals"], total_cost=req.get("total_cost"),
                  transport_per_q=req.get("transport_cost_per_quintal") or 0.0,
                  fee_pct=req.get("market_fee_pct") or 0.0)
    now = scenario(days=0, price=latest, low=None, high=None, storage_per_q_month=0, loss_pct_per_30=0, **common)
    now.update({"label": "Sell now (latest recorded price)", "source": "latest observation"})

    scenarios = []
    if opt["id"] != "sell_now":
        for h in fc["horizons"]:
            entry: dict[str, Any] = {"days": h["horizon_days"]}
            if not h["available"]:
                entry.update({"possible": False, "reason": "No evaluated forecast for this horizon."})
            elif max_days is not None and h["horizon_days"] > max_days:
                entry.update({"possible": False, "reason": f"{opt['name']} keeps this produce about {max_days} days."})
            else:
                iv = h["interval"] or {}
                s = scenario(days=h["horizon_days"], price=h["modal_price"], low=iv.get("lower"), high=iv.get("upper"),
                             storage_per_q_month=cost, loss_pct_per_30=loss, **common)
                s.update({
                    "possible": True,
                    "vs_sell_now": round(s["net_revenue"] - now["net_revenue"], 2),
                    "forecast_beats_naive_on_test": h["beats_naive_on_test"],
                    "forecast_test_mape": h["test_metrics_overall"]["mape"],
                    "storage_life_unknown": max_days is None,
                })
                entry = s
            scenarios.append(entry)
    return {
        "series": fc["series"],
        "latest_observation": fc["latest_observation"],
        "storage_option": {**opt, "used_cost_per_quintal_per_month": cost, "used_loss_pct_per_30_days": loss,
                           "used_max_days": max_days},
        "sell_now": now,
        "scenarios": scenarios,
        "model_version": fc["model_version"],
        "data_cutoff": fc["data_cutoff"],
        "assumptions": [
            "Loss is spread evenly over time (linear); real spoilage often speeds up later.",
            "Store-later prices are model forecasts with their tested error, not guarantees.",
            "Sell-now uses the latest recorded price for this mandi, which may be older than today.",
        ],
    }
