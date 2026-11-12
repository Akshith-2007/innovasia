"""Cold-storage device state, telemetry log, auto thermostat and PCM backup estimate (ADR-024).

Files only (no database): data/device/state.json (atomic writes) and data/device/telemetry/YYYY-MM-DD.csv.
shortcut: single device and a process-wide lock; add a device id and per-device files before running several chambers.
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import InputRequiredError

_lock = Lock()
FIELDS = ["received_at", "chamber_temp_c", "humidity_pct", "coil_temp_c", "pump_on_reported", "pump_on_desired",
          "mode", "pcm_remaining_h", "pcm_soc", "heat_load_w"]
MAX_PCM_STEP_SECONDS = 300  # longer gaps mean the device was offline; we don't know what happened then

DEFAULT_STATE: dict[str, Any] = {
    "mode": "manual",
    "pump_on": False,
    "auto": {"upper_c": None, "lower_c": None},
    # Physics inputs (ADR-025): nothing assumed; the estimate appears once these are entered.
    "pcm": {"mass_kg": None, "latent_kj_per_kg": None, "melt_c": None, "ambient_c": None,
            "wall_area_m2": None, "insulation_mm": None, "insulation_k": None, "coil_w_per_k": None,
            "state_of_charge": 1.0, "updated_at": None},
    "last_seen": None,
    "last_reading": None,
}


def _dir() -> Path:
    d = get_settings().data_dir / "device"
    (d / "telemetry").mkdir(parents=True, exist_ok=True)
    return d


def _now() -> datetime:
    return datetime.now(timezone.utc)


def load_state() -> dict[str, Any]:
    p = _dir() / "state.json"
    if not p.exists():
        return json.loads(json.dumps(DEFAULT_STATE))
    state = json.loads(p.read_text(encoding="utf-8"))
    for k, v in DEFAULT_STATE.items():  # tolerate older state files
        state.setdefault(k, v)
    for k, v in DEFAULT_STATE["pcm"].items():
        state["pcm"].setdefault(k, v)
    return state


def _save_state(state: dict[str, Any]) -> None:
    p = _dir() / "state.json"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    os.replace(tmp, p)  # atomic: a crash never leaves a half-written state file


PCM_FIELDS = ("mass_kg", "latent_kj_per_kg", "melt_c", "ambient_c", "wall_area_m2", "insulation_mm", "insulation_k")


def pcm_physics(pcm: dict[str, Any], chamber: float | None, coil: float | None, pump_on: bool) -> dict[str, Any]:
    """Energy balance of the PCM chamber.

    capacity  E = m * L                         (kJ, latent heat only)
    heat in   Q = UA * (T_ambient - T_chamber), UA = area * k / thickness   (W)
    recharge  P = coil_UA * (T_melt - T_coil) while the pump runs and the coil is colder than the melt point (W)
    backup    t = remaining E / Q               (h)
    """
    missing = [f for f in PCM_FIELDS if pcm.get(f) is None]
    if missing:
        return {"configured": False, "missing": missing}
    capacity_kj = pcm["mass_kg"] * pcm["latent_kj_per_kg"]
    ua = pcm["wall_area_m2"] * pcm["insulation_k"] / (pcm["insulation_mm"] / 1000)
    t_in = chamber if chamber is not None else pcm["melt_c"]
    load_w = max(0.0, ua * (pcm["ambient_c"] - t_in))
    charge_w = None
    if pcm.get("coil_w_per_k") is not None and coil is not None:
        charge_w = pcm["coil_w_per_k"] * max(0.0, pcm["melt_c"] - coil) if pump_on else 0.0
    remaining_kj = capacity_kj * pcm["state_of_charge"]
    return {
        "configured": True,
        "capacity_kj": round(capacity_kj, 1),
        "remaining_kj": round(remaining_kj, 1),
        "state_of_charge": pcm["state_of_charge"],
        "ua_w_per_k": round(ua, 3),
        "heat_load_w": round(load_w, 1),
        "charge_w": None if charge_w is None else round(charge_w, 1),
        "remaining_hours": round(remaining_kj * 1000 / load_w / 3600, 2) if load_w > 0 else None,
        "full_backup_hours": round(capacity_kj * 1000 / load_w / 3600, 2) if load_w > 0 else None,
    }


def _update_pcm(state: dict[str, Any], now: datetime, chamber: float | None, coil: float | None, pump_on: bool) -> None:
    """Advance the PCM state of charge by the net energy flow since the previous reading."""
    pcm = state["pcm"]
    last = pcm.get("updated_at")
    pcm["updated_at"] = now.isoformat()
    phys = pcm_physics(pcm, chamber, coil, pump_on)
    if not last or not phys["configured"]:
        return
    dt = (now - datetime.fromisoformat(last)).total_seconds()
    if dt <= 0 or dt > MAX_PCM_STEP_SECONDS:
        return
    charge = phys["charge_w"] or 0.0  # unknown coil transfer = no modelled recharge
    net_kj = (charge - phys["heat_load_w"]) * dt / 1000
    pcm["state_of_charge"] = min(1.0, max(0.0, pcm["state_of_charge"] + net_kj / phys["capacity_kj"]))


def record_telemetry(reading: dict[str, Any]) -> dict[str, Any]:
    """Store one device reading, run the auto thermostat, and return the command the device should apply."""
    now = _now()
    with _lock:
        state = load_state()
        chamber = reading.get("chamber_temp_c")
        auto = state["auto"]
        if state["mode"] == "auto" and chamber is not None and auto["upper_c"] is not None:
            if chamber > auto["upper_c"]:
                state["pump_on"] = True
            elif chamber < auto["lower_c"]:
                state["pump_on"] = False
        _update_pcm(state, now, chamber, reading.get("coil_temp_c"), bool(reading.get("pump_on")))
        phys = pcm_physics(state["pcm"], chamber, reading.get("coil_temp_c"), bool(reading.get("pump_on")))
        state["last_seen"] = now.isoformat()
        state["last_reading"] = {**reading, "received_at": now.isoformat()}
        _save_state(state)
        path = _dir() / "telemetry" / f"{now:%Y-%m-%d}.csv"
        new = not path.exists()
        with path.open("a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            if new:
                w.writerow(FIELDS)
            w.writerow([now.isoformat(), chamber, reading.get("humidity_pct"), reading.get("coil_temp_c"),
                        int(bool(reading.get("pump_on"))), int(state["pump_on"]), state["mode"],
                        phys.get("remaining_hours"), round(state["pcm"]["state_of_charge"], 4),
                        phys.get("heat_load_w")])
        return command(state)


def command(state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state or load_state()
    return {"pump_on": bool(state["pump_on"]), "mode": state["mode"]}


def update_control(change: dict[str, Any]) -> dict[str, Any]:
    with _lock:
        state = load_state()
        auto = {**state["auto"], **{k: v for k, v in (change.get("auto") or {}).items() if k in ("upper_c", "lower_c")}}
        if auto["upper_c"] is not None and auto["lower_c"] is not None and auto["lower_c"] >= auto["upper_c"]:
            raise InputRequiredError("Lower limit must be below the upper limit.", {"field": "auto"})
        mode = change.get("mode", state["mode"])
        if mode == "auto" and (auto["upper_c"] is None or auto["lower_c"] is None):
            raise InputRequiredError("Set both temperature limits before switching to automatic mode.", {"field": "auto"})
        state["auto"] = auto
        state["mode"] = mode
        if change.get("pump_on") is not None:
            state["mode"] = "manual"  # a manual press always overrides auto
            state["pump_on"] = bool(change["pump_on"])
        pcm_change = {k: v for k, v in (change.get("pcm") or {}).items() if k in (*PCM_FIELDS, "coil_w_per_k")}
        state["pcm"].update(pcm_change)
        if change.get("pcm_reset_full"):
            state["pcm"]["state_of_charge"] = 1.0
        _save_state(state)
        return state


def recommendations(state: dict[str, Any], online: bool) -> list[dict[str, str]]:
    tips: list[dict[str, str]] = []
    r = state.get("last_reading") or {}
    if not online:
        tips.append({"level": "warn", "text": "No data from the ESP32 recently. Check its power and Wi-Fi. "
                                              "The pump keeps its last state until the device reconnects."})
        return tips
    chamber, coil, reported = r.get("chamber_temp_c"), r.get("coil_temp_c"), bool(r.get("pump_on"))
    if chamber is None:
        tips.append({"level": "warn", "text": "Chamber sensor (DHT11) reading failed. Check its wiring."})
    if coil is None:
        tips.append({"level": "warn", "text": "Coil sensor (DS18B20) not detected. Check its wiring."})
    if reported != bool(state["pump_on"]):
        tips.append({"level": "info", "text": "The device has not applied the latest pump command yet."})
    if reported and chamber is not None and coil is not None and coil >= chamber - 0.5:
        tips.append({"level": "warn", "text": f"Coil water ({coil:.1f}°C) is not colder than the chamber "
                                              f"({chamber:.1f}°C). Pumping now only moves heat in and uses power. "
                                              "Re-cool the reservoir or switch the pump off."})
    up, lo = state["auto"]["upper_c"], state["auto"]["lower_c"]
    if chamber is not None and up is not None and chamber > up and not reported:
        tips.append({"level": "warn", "text": f"Chamber is above your {up:g}°C limit and the pump is off. Turn it on."})
    if chamber is not None and lo is not None and chamber < lo and reported:
        tips.append({"level": "ok", "text": f"Chamber is below your {lo:g}°C limit. Switching the pump off saves power."})
    phys = pcm_physics(state["pcm"], chamber, coil, reported)
    if not phys["configured"]:
        tips.append({"level": "info", "text": "Enter the PCM and chamber details to get a backup-time estimate."})
    elif phys["remaining_hours"] is not None and phys["remaining_hours"] < 1 and not reported:
        tips.append({"level": "warn", "text": f"Estimated PCM backup is {phys['remaining_hours'] * 60:.0f} minutes at the "
                                              f"current heat load ({phys['heat_load_w']:.0f} W). Run the pump to recharge it."})
    elif reported and phys["configured"] and phys.get("charge_w") == 0.0:
        tips.append({"level": "warn", "text": "The coil is not colder than the PCM melting point, so pumping is not "
                                              "recharging the PCM. Cool the water first."})
    if not tips:
        tips.append({"level": "ok", "text": "Everything is within your limits."})
    return tips


def status() -> dict[str, Any]:
    state = load_state()
    last = state.get("last_seen")
    age = (_now() - datetime.fromisoformat(last)).total_seconds() if last else None
    online = age is not None and age <= get_settings().device_offline_after_seconds
    r = state.get("last_reading") or {}
    phys = pcm_physics(state["pcm"], r.get("chamber_temp_c"), r.get("coil_temp_c"), bool(r.get("pump_on")))
    return {**state, "online": online, "seconds_since_seen": age, "recommendations": recommendations(state, online),
            "pcm_estimate": phys,
            "pcm_note": "Physics estimate from the values you entered (latent heat only, steady heat leak through "
                        "insulation, outside temperature as entered). Not a measurement."}


def telemetry(hours: float) -> list[dict[str, Any]]:
    since = _now() - timedelta(hours=hours)
    rows: list[dict[str, Any]] = []
    day = since.date()
    while day <= _now().date():
        path = _dir() / "telemetry" / f"{day:%Y-%m-%d}.csv"
        if path.exists():
            with path.open(encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    if datetime.fromisoformat(r["received_at"]) >= since:
                        rows.append({k: (None if v in ("", "None") else v) for k, v in r.items()})
        day += timedelta(days=1)
    for r in rows:
        for k in ("chamber_temp_c", "humidity_pct", "coil_temp_c", "pcm_remaining_h", "pcm_soc", "heat_load_w"):
            r[k] = float(r[k]) if r.get(k) is not None else None
        for k in ("pump_on_reported", "pump_on_desired"):
            r[k] = r[k] == "1"
    return rows
