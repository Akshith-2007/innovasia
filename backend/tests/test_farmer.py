"""Farmer lots and sale plans (ADR-027). Series are TEST VALUES in temp dirs."""

from datetime import date, timedelta

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.ml import training
from app.services import farmer_service as fs
from app.services import geo
from tests.conftest import make_test_series

ADM = {"X-Admin-Password": "admin-secret"}
START = date(2025, 1, 1)
N = 420
LAST = START + timedelta(days=N - 1)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "admin-secret")
    get_settings.cache_clear()
    s = get_settings()
    s.processed_dir.mkdir(parents=True)
    near = make_test_series(N, market="Near", commodity="Onion", start=START)
    far = make_test_series(N, market="Far", commodity="Onion", start=START)
    far["district"] = "Far District"
    pd.concat([near, far]).to_parquet(s.market_prices_path, index=False)
    training.train(s.market_prices_path, s.models_dir, ("random_forest",))
    return TestClient(app)


def test_road_km_is_plausible():
    km = geo.road_km(("Telangana", "Warangal"), ("Telangana", "Hyderabad"))
    assert 120 < km < 200  # real road distance is ~150 km
    assert geo.road_km(("Telangana", "Warangal"), ("Nowhere", "X")) is None


def test_lots_need_admin_and_valid_input(client):
    assert client.get("/api/v1/admin/farmer/lots").status_code == 401
    bad = client.post("/api/v1/admin/farmer/lots", headers=ADM, json={"farmer_name": "A", "village": "V", "commodity": "Onion",
                                                               "quantity_q": -5, "entry_date": "2026-01-01"})
    assert bad.status_code == 422


def test_plan_requires_settings_then_ranks_mandis(client):
    lot = client.post("/api/v1/admin/farmer/lots", headers=ADM, json={
        "farmer_name": "Test Farmer", "village": "Test Village", "commodity": "Onion",
        "quantity_q": 10, "entry_date": str(LAST - timedelta(days=10))}).json()["data"]
    r = client.get(f"/api/v1/admin/farmer/lots/{lot['id']}/plan", headers=ADM)
    assert r.status_code == 422 and "storage_district" in r.json()["error"]["details"]["fields"]

    client.put("/api/v1/admin/farmer/settings", headers=ADM, json={
        "storage_state": "Telangana", "storage_district": "Warangal", "transport_per_q_km": 2,
        "storage_rent_per_q_month": 30, "loss_pct_per_30_days": 3, "market_fee_pct": 2,
        "km_overrides": {"Test State|Test District|Near": 10, "Test State|Far District|Far": 300}})
    p = fs.plan(lot["id"], today=LAST + timedelta(days=1))
    assert [m["market"] for m in p["mandis"]] == ["Near", "Far"]  # same prices, so the nearer mandi wins
    near = p["mandis"][0]
    now = near["options"][0]
    # 11 days stored: loss 3%*11/30, storage 10q*30*11/30 = 110, transport 10q*10km*2 = 200
    sellable = 10 * (1 - 0.03 * 11 / 30)
    assert now["transport_cost"] == pytest.approx(200) and now["storage_cost"] == pytest.approx(110)
    assert now["net_revenue"] == pytest.approx(sellable * now["price_per_quintal"] * 0.98 - 310, abs=0.05)
    assert now["total_selling_cost"] == pytest.approx(now["transport_cost"] + now["storage_cost"] + now["market_fee"])
    assert {o["sell_after_days"] for o in near["options"]} == {0, 7, 14, 30}
    assert p["recommendation"]["market"] == "Near" and near["km_source"] == "override"

    client.put("/api/v1/admin/farmer/settings", headers=ADM, json={"max_km": 50})
    p2 = fs.plan(lot["id"], today=LAST + timedelta(days=1))
    assert [m["market"] for m in p2["mandis"]] == ["Near"] and p2["skipped"]["too_far"] == 1


def test_unknown_district_rejected(client):
    r = client.put("/api/v1/admin/farmer/settings", headers=ADM, json={"storage_state": "Telangana", "storage_district": "Atlantis"})
    assert r.status_code == 422


def test_delete_lot(client):
    lot = client.post("/api/v1/admin/farmer/lots", headers=ADM, json={"farmer_name": "A", "village": "V", "commodity": "Onion",
                                                               "quantity_q": 1, "entry_date": "2026-01-01"}).json()["data"]
    assert client.delete(f"/api/v1/admin/farmer/lots/{lot['id']}", headers=ADM).status_code == 200
    assert client.get("/api/v1/admin/farmer/lots", headers=ADM).json()["data"] == []
    assert client.delete(f"/api/v1/admin/farmer/lots/{lot['id']}", headers=ADM).status_code == 404
