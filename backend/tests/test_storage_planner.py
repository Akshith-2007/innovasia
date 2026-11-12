"""Storage planner (ADR-023). Money math is checked by hand; series are TEST VALUES in temp dirs."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.ml import training
from app.services import storage_planner as sp
from tests.conftest import make_test_series


def test_categories():
    assert sp.commodity_category("Onion") == "onion"
    assert sp.commodity_category("Dry Chillies") == "dry_chilli"
    assert sp.commodity_category("Green Chilli") == "perishable"
    assert sp.commodity_category("Paddy (Dhan)(Common)") == "grain_pulse"
    assert sp.commodity_category("Coriander Seed") == "grain_pulse"
    assert sp.commodity_category("Unknown Thing") == "other"


def test_defaults_are_cited_or_missing():
    opts = {o["id"]: o for o in sp.options_for("Onion")["options"]}
    assert opts["cold_storage"]["default_loss_pct_per_30_days"] == pytest.approx(1.25)  # 5% over 120 days
    assert opts["cold_storage"]["sources"]
    assert opts["cold_storage"]["default_cost_per_quintal_per_month"] is None  # chilli rent is not onion rent
    chilli = {o["id"]: o for o in sp.options_for("Dry Chillies")["options"]}
    assert chilli["cold_storage"]["default_cost_per_quintal_per_month"] == 40.0
    assert opts["warehouse"]["suited"] is False
    assert sp.options_for("Paddy (Dhan)(Common)")["options"][5]["default_loss_pct_per_30_days"] is None


def test_scenario_math():
    s = sp.scenario(days=30, price=2000, low=1800, high=2200, quantity=10, total_cost=15000,
                    transport_per_q=50, fee_pct=2, storage_per_q_month=40, loss_pct_per_30=5)
    # sellable 9.5 q; gross 19000; fee 380; transport 500; storage 400 -> net 17720
    assert s["sellable_quintals"] == pytest.approx(9.5)
    assert s["net_revenue"] == pytest.approx(17720)
    assert s["net_revenue_low"] == pytest.approx(9.5 * 1800 * 0.98 - 900)
    assert s["profit"] == pytest.approx(2720)
    assert s["break_even_price"] == pytest.approx((15000 + 500 + 400) / (9.5 * 0.98), rel=1e-4)


@pytest.fixture
def trained():
    s = get_settings()
    s.processed_dir.mkdir(parents=True)
    make_test_series(420, market="A", commodity="Onion").to_parquet(s.market_prices_path, index=False)
    training.train(s.market_prices_path, s.models_dir, ("random_forest",))
    return TestClient(app)


BODY = {"state": "Test State", "market": "A", "commodity": "Onion", "quantity_quintals": 10, "total_cost": 15000}


def test_plan_endpoint(trained):
    r = trained.post("/api/v1/decision/plan", json={**BODY, "storage_option": "cold_storage"})
    assert r.status_code == 422 and r.json()["error"]["details"]["field"] == "storage_cost_per_quintal_per_month"
    r = trained.post("/api/v1/decision/plan",
                     json={**BODY, "storage_option": "cold_storage", "storage_cost_per_quintal_per_month": 35})
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["sell_now"]["days"] == 0 and d["sell_now"]["profit"] is not None
    possible = [x for x in d["scenarios"] if x.get("possible")]
    assert possible and all("vs_sell_now" in x for x in possible)
    assert d["storage_option"]["used_loss_pct_per_30_days"] == pytest.approx(1.25)


def test_plan_requires_loss_when_no_source(trained):
    r = trained.post("/api/v1/decision/plan", json={**BODY, "commodity": "Onion", "storage_option": "zecc"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "input_required"
    ok = trained.post("/api/v1/decision/plan", json={**BODY, "storage_option": "zecc", "loss_pct_per_30_days": 10})
    assert ok.status_code == 200


def test_plan_rejects_bad_input(trained):
    assert trained.post("/api/v1/decision/plan", json={**BODY, "quantity_quintals": 0, "storage_option": "warehouse"}).status_code == 422
    assert trained.post("/api/v1/decision/plan", json={**BODY, "storage_option": "spaceship"}).status_code == 404
