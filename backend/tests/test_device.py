"""Cold-storage device + admin portal (ADR-024). Readings are TEST VALUES in temp dirs."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.services import device_service as ds

DEV = {"X-Device-Key": "dev-secret"}
ADM = {"X-Admin-Password": "admin-secret"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DEVICE_KEY", "dev-secret")
    monkeypatch.setenv("ADMIN_PASSWORD", "admin-secret")
    get_settings.cache_clear()
    return TestClient(app)


def reading(chamber=8.0, coil=4.0, pump_on=False, humidity=90.0):
    return {"chamber_temp_c": chamber, "coil_temp_c": coil, "humidity_pct": humidity, "pump_on": pump_on}


def test_auth_required(client):
    assert client.post("/api/v1/device/telemetry", json=reading()).status_code == 401
    assert client.post("/api/v1/device/telemetry", json=reading(), headers={"X-Device-Key": "nope"}).status_code == 401
    assert client.get("/api/v1/admin/device").status_code == 401
    assert client.get("/api/v1/admin/device", headers=DEV).status_code == 401  # device key is not admin


def test_disabled_without_secrets():
    c = TestClient(app)
    assert c.get("/api/v1/device/command", headers=DEV).json()["error"]["code"] == "not_configured"


def test_manual_and_auto_control(client):
    r = client.put("/api/v1/admin/device/control", json={"mode": "auto"}, headers=ADM)
    assert r.status_code == 422  # limits must be set first, never assumed
    client.put("/api/v1/admin/device/control", json={"mode": "auto", "auto": {"upper_c": 10, "lower_c": 6}}, headers=ADM)
    assert client.post("/api/v1/device/telemetry", json=reading(chamber=11), headers=DEV).json()["pump_on"] is True
    assert client.post("/api/v1/device/telemetry", json=reading(chamber=8, pump_on=True), headers=DEV).json()["pump_on"] is True  # hysteresis
    assert client.post("/api/v1/device/telemetry", json=reading(chamber=5.5, pump_on=True), headers=DEV).json()["pump_on"] is False
    # manual press overrides auto
    s = client.put("/api/v1/admin/device/control", json={"pump_on": True}, headers=ADM).json()["data"]
    assert s["mode"] == "manual" and s["pump_on"] is True
    assert client.get("/api/v1/device/command", headers=DEV).json() == {"pump_on": True, "mode": "manual"}
    bad = client.put("/api/v1/admin/device/control", json={"auto": {"upper_c": 5, "lower_c": 6}}, headers=ADM)
    assert bad.status_code == 422


PCM = {"mass_kg": 10, "latent_kj_per_kg": 334, "melt_c": 5, "ambient_c": 30,
       "wall_area_m2": 2, "insulation_mm": 50, "insulation_k": 0.025, "coil_w_per_k": 40}


def test_pcm_physics_values():
    p = ds.pcm_physics({**PCM, "state_of_charge": 1.0}, chamber=10, coil=2, pump_on=False)
    # UA = 2 * 0.025 / 0.05 = 1 W/K; load = 1 * (30 - 10) = 20 W; E = 3340 kJ -> 3340e3 / 20 / 3600 h
    assert p["ua_w_per_k"] == pytest.approx(1.0) and p["heat_load_w"] == pytest.approx(20.0)
    assert p["capacity_kj"] == pytest.approx(3340) and p["full_backup_hours"] == pytest.approx(46.39, abs=0.01)
    assert ds.pcm_physics({**PCM, "state_of_charge": 1.0}, 10, 2, True)["charge_w"] == pytest.approx(120)  # 40*(5-2)
    assert ds.pcm_physics({**PCM, "state_of_charge": 1.0}, 10, 6, True)["charge_w"] == 0.0  # coil warmer than melt
    assert ds.pcm_physics({"state_of_charge": 1.0}, 10, 2, False) == {"configured": False, "missing": list(ds.PCM_FIELDS)}


def test_pcm_energy_balance_over_time(client, monkeypatch):
    clock = {"t": datetime(2026, 1, 1, tzinfo=timezone.utc)}
    monkeypatch.setattr(ds, "_now", lambda: clock["t"])
    d = client.get("/api/v1/admin/device", headers=ADM).json()["data"]
    assert d["pcm_estimate"]["configured"] is False  # nothing assumed
    client.put("/api/v1/admin/device/control", json={"pcm": PCM}, headers=ADM)
    client.post("/api/v1/device/telemetry", json=reading(chamber=10, coil=2), headers=DEV)
    for _ in range(12):  # 1 h pump off at 20 W -> 72 kJ drained
        clock["t"] += timedelta(minutes=5)
        client.post("/api/v1/device/telemetry", json=reading(chamber=10, coil=2), headers=DEV)
    soc = ds.load_state()["pcm"]["state_of_charge"]
    assert soc == pytest.approx(1 - 72 / 3340)
    for _ in range(12):  # 1 h pumping: +120 W charge -20 W load = +100 W -> +360 kJ, capped at full
        clock["t"] += timedelta(minutes=5)
        client.post("/api/v1/device/telemetry", json=reading(chamber=10, coil=2, pump_on=True), headers=DEV)
    assert ds.load_state()["pcm"]["state_of_charge"] == pytest.approx(1.0)
    clock["t"] += timedelta(hours=3)  # offline gap is not counted
    client.post("/api/v1/device/telemetry", json=reading(chamber=10, coil=2), headers=DEV)
    assert ds.load_state()["pcm"]["state_of_charge"] == pytest.approx(1.0)
    est = client.get("/api/v1/admin/device", headers=ADM).json()["data"]["pcm_estimate"]
    assert est["remaining_hours"] == pytest.approx(46.39, abs=0.01)
    assert client.put("/api/v1/admin/device/control", json={"pcm": {"insulation_k": 5}}, headers=ADM).status_code == 422


def test_status_tips_and_telemetry(client):
    client.post("/api/v1/device/telemetry", json=reading(chamber=9, coil=12, pump_on=True), headers=DEV)
    d = client.get("/api/v1/admin/device", headers=ADM).json()["data"]
    assert d["online"] is True and "not colder than the chamber" in " ".join(t["text"] for t in d["recommendations"])
    assert "Physics estimate" in d["pcm_note"] and "Not a measurement" in d["pcm_note"]
    rows = client.get("/api/v1/admin/telemetry?hours=1", headers=ADM).json()["data"]
    assert rows[-1]["coil_temp_c"] == 12.0 and rows[-1]["pump_on_reported"] is True


def test_rejects_impossible_readings(client):
    assert client.post("/api/v1/device/telemetry", json=reading(humidity=150), headers=DEV).status_code == 422
