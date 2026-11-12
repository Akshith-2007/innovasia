import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.ml import training
from tests.conftest import make_test_series

client = TestClient(app)


def test_health_without_data():
    body = client.get("/api/v1/health").json()
    assert body["status"] == "ok"
    assert body["data"]["market_prices"] is False
    assert body["model"]["available"] is False


def test_endpoints_report_missing_data_honestly():
    r = client.get("/api/v1/markets/states")
    assert r.status_code == 503 and r.json()["error"]["code"] == "data_unavailable"
    r = client.post("/api/v1/ml/predict", json={"state": "x", "market": "y", "commodity": "z"})
    assert r.status_code == 503 and r.json()["error"]["code"] == "model_unavailable"
    assert client.get("/api/v1/ml/metrics").status_code == 503


@pytest.fixture
def processed():
    s = get_settings()
    s.processed_dir.mkdir(parents=True)
    df = pd.concat([make_test_series(420, market="A"), make_test_series(40, market="Short")])
    df.to_parquet(s.market_prices_path, index=False)
    return s


def test_history_and_sources(processed):
    r = client.get("/api/v1/market/history", params={"state": "Test State", "market": "A",
                                                    "commodity": "Test Commodity", "start": "2020-02-01",
                                                    "end": "2020-02-10"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["data"]) == 10
    assert body["source"]["cached"] is True and body["source"]["live"] is False
    assert body["data"][0]["arrival_date"] == "2020-02-01"


def test_prices_fallback_is_labelled(processed):
    r = client.get("/api/v1/market/prices", params={"state": "Test State", "market": "A"})
    body = r.json()
    assert r.status_code == 200
    assert body["source"]["cached"] is True
    assert body["meta"]["live_error"]["code"] == "not_configured"


def test_unknown_series_404(processed):
    r = client.get("/api/v1/market/history", params={"state": "Test State", "market": "Nope", "commodity": "x"})
    assert r.status_code == 404


def test_predict_schema_and_insufficient_series(processed):
    training.train(processed.market_prices_path, processed.models_dir, ("random_forest",))
    ok = client.post("/api/v1/ml/predict", json={"state": "Test State", "market": "A", "commodity": "Test Commodity"})
    assert ok.status_code == 200, ok.text
    d = ok.json()["data"]
    assert d["prediction"]["modal_price"] > 0
    assert d["model"]["version"] and d["model"]["data_cutoff"] and d["latest_observation"]["date"]
    short = client.post("/api/v1/ml/predict",
                        json={"state": "Test State", "market": "Short", "commodity": "Test Commodity"})
    assert short.status_code == 422 and short.json()["error"]["code"] == "insufficient_data"
    assert client.get("/api/v1/ml/metrics").json()["data"]["results"]["naive_last"]["test"]["n"] > 0


def test_rate_limit_returns_429_with_retry_after():
    from fastapi import FastAPI

    from app.core.rate_limit import RateLimitMiddleware

    mini = FastAPI()
    mini.add_middleware(RateLimitMiddleware, per_minute=3)

    @mini.get("/api/v1/x")
    def x():
        return {"ok": True}

    @mini.get("/api/v1/health")
    def h():
        return {"ok": True}

    c = TestClient(mini)
    assert [c.get("/api/v1/x").status_code for _ in range(3)] == [200, 200, 200]
    r = c.get("/api/v1/x")
    assert r.status_code == 429 and r.json()["error"]["code"] == "rate_limited"
    assert int(r.headers["retry-after"]) >= 1
    assert c.get("/api/v1/health").status_code == 200  # health is exempt


def test_two_grades_ask_user_to_choose(processed):
    s = processed
    a = make_test_series(420, market="A")
    b = a.assign(grade="Large")
    pd.concat([a, b]).to_parquet(s.market_prices_path, index=False)
    training.train(s.market_prices_path, s.models_dir, ("random_forest",), horizon_list=())
    r = client.post("/api/v1/decision/forecast-horizons", json={"state": "Test State", "market": "A", "commodity": "Test Commodity"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "ambiguous_series"
    assert {o["grade"] for o in r.json()["error"]["details"]["options"]} == {"FAQ", "Large"}
    ok = client.post("/api/v1/decision/forecast-horizons",
                     json={"state": "Test State", "market": "A", "commodity": "Test Commodity", "grade": "Large"})
    assert ok.status_code == 200
