"""Farmer lots and best-mandi comparison (ADR-026). Series are TEST VALUES in temp dirs."""

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.ml import training
from tests.conftest import make_test_series

ADM = {"X-Admin-Password": "admin-secret"}
LOT = {
    "farmer_name": "Test Farmer", "phone": "+91 90000 00000", "village": "Test Village", "state": "Test State",
    "latitude": 17.4, "longitude": 78.5, "commodity": "Onion", "quantity_quintals": 10,
    "total_cost": 15000, "transport_rate_per_quintal_km": 2,
    "mandis": [{"market": "A", "distance_km": 10}, {"market": "B", "distance_km": 100},
               {"market": "Nowhere", "distance_km": 5}],
}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "admin-secret")
    get_settings.cache_clear()
    s = get_settings()
    s.processed_dir.mkdir(parents=True)
    a = make_test_series(420, market="A", commodity="Onion")
    b = make_test_series(420, market="B", commodity="Onion")
    b["modal_price"] += 100  # B pays more per quintal
    b["min_price"] += 100
    b["max_price"] += 100
    pd.concat([a, b]).to_parquet(s.market_prices_path, index=False)
    training.train(s.market_prices_path, s.models_dir, ("random_forest",))
    return TestClient(app)


def test_admin_only(client):
    assert client.get("/api/v1/admin/lots").status_code == 401
    assert client.post("/api/v1/admin/lots", json=LOT).status_code == 401


def test_add_compare_delete(client):
    lot = client.post("/api/v1/admin/lots", json=LOT, headers=ADM).json()["data"]
    assert [x["id"] for x in client.get("/api/v1/admin/lots", headers=ADM).json()["data"]] == [lot["id"]]

    r = client.get(f"/api/v1/admin/lots/{lot['id']}/compare", headers=ADM).json()["data"]
    rows = {m["market"]: m for m in r["mandis"]}
    assert rows["Nowhere"]["available"] is False  # no series: reported, never borrowed from another mandi
    a, b = rows["A"]["best"], rows["B"]["best"]
    assert a["transport_cost"] == pytest.approx(10 * 2 * 10)   # qty x rate x km
    assert b["transport_cost"] == pytest.approx(10 * 2 * 100)
    # B: +100/q on 10 q = +1000 gross, but 1800 more transport -> A wins
    assert r["recommendation"]["market"] == "A"
    assert r["recommendation"]["margin_over_next_best"] == pytest.approx(a["net_revenue"] - b["net_revenue"])

    assert client.delete(f"/api/v1/admin/lots/{lot['id']}", headers=ADM).status_code == 200
    assert client.get(f"/api/v1/admin/lots/{lot['id']}/compare", headers=ADM).status_code == 404


def test_validation(client):
    bad = {**LOT, "mandis": []}
    assert client.post("/api/v1/admin/lots", json=bad, headers=ADM).status_code == 422
    no_phone = {k: v for k, v in LOT.items() if k != "phone"}
    assert client.post("/api/v1/admin/lots", json=no_phone, headers=ADM).status_code == 422  # phone is required


def test_storage_option_adds_forecast_horizons(client):
    lot = client.post("/api/v1/admin/lots", json={**LOT, "storage_option": "home_ambient"}, headers=ADM).json()["data"]
    r = client.get(f"/api/v1/admin/lots/{lot['id']}/compare", headers=ADM).json()["data"]
    a = next(m for m in r["mandis"] if m["market"] == "A")
    assert a["options"][0]["days"] == 0 and len(a["options"]) > 1  # sell now + forecast horizons
    assert a["best"]["net_revenue"] == max(o["net_revenue"] for o in a["options"])
