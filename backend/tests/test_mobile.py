"""Raithanna mobile endpoints (ADR-030). Series and lots are TEST VALUES in temp dirs; Bedrock/Azure are faked."""

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.ml import training
from app.services import advisory_script as S
from app.services import mobile_service, narration, tts
from tests.conftest import make_test_series

ADM = {"X-Admin-Password": "admin-secret"}
LOT = {
    "farmer_name": "Test Farmer", "phone": "+91 98480 12345", "village": "Test Village", "state": "Test State",
    "commodity": "Onion", "quantity_quintals": 10, "total_cost": 15000, "transport_rate_per_quintal_km": 2,
    "market_fee_pct": 2, "storage_option": "home_ambient",
    "mandis": [{"market": "A", "distance_km": 10}, {"market": "B", "distance_km": 100},
               {"market": "Nowhere", "distance_km": 5}],
}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "admin-secret")
    monkeypatch.setenv("MOBILE_LINK_SECRET", "test-secret")
    get_settings.cache_clear()
    mobile_service._compare_cache.clear()
    s = get_settings()
    s.processed_dir.mkdir(parents=True)
    a = make_test_series(420, market="A", commodity="Onion")
    b = make_test_series(420, market="B", commodity="Onion")
    for col in ("modal_price", "min_price", "max_price"):
        b[col] += 100
    pd.concat([a, b]).to_parquet(s.market_prices_path, index=False)
    training.train(s.market_prices_path, s.models_dir, ("random_forest",))
    c = TestClient(app)
    c.post("/api/v1/admin/lots", json=LOT, headers=ADM).raise_for_status()
    return c


def _identify(c, name="Test Farmer", phone="9848012345"):
    return c.post("/api/v1/mobile/identify", json={"name": name, "phone": phone})


def _auth(c):
    lot = _identify(c).json()["data"][0]
    return lot["lot_id"], {"X-Farmer-Token": lot["token"]}


def test_identify_needs_name_and_phone(client):
    r = _identify(client, phone="+91-98480-12345").json()["data"]
    assert len(r) == 1 and r[0]["commodity"] == "Onion" and r[0]["crop_te"] == "ఉల్లిపాయ" and r[0]["token"]
    assert "phone" not in r[0]
    for name, phone in [("Someone Else", "9848012345"), ("Test Farmer", "9000000000")]:
        bad = _identify(client, name, phone)
        assert bad.status_code == 404 and bad.json()["error"]["code"] == "farmer_not_registered"
        assert bad.json()["error"]["message"] == S.not_registered("te")


def test_disabled_without_secret(client, monkeypatch):
    monkeypatch.setenv("MOBILE_LINK_SECRET", "")
    get_settings.cache_clear()
    assert _identify(client).json()["error"]["code"] == "not_configured"


def test_token_required_and_bound_to_lot(client):
    lot_id, h = _auth(client)
    assert client.get(f"/api/v1/mobile/lots/{lot_id}").status_code == 401
    assert client.get(f"/api/v1/mobile/lots/{lot_id}", headers={"X-Farmer-Token": "0" * 40}).status_code == 401
    other = client.post("/api/v1/admin/lots", json={**LOT, "phone": "9000000001"}, headers=ADM).json()["data"]
    assert client.get(f"/api/v1/mobile/lots/{other['id']}", headers=h).status_code == 401  # my token, their lot


def test_lot_view_uses_backend_figures(client):
    lot_id, h = _auth(client)
    v = client.get(f"/api/v1/mobile/lots/{lot_id}", headers=h).json()["data"]
    assert "phone" not in v["lot"]
    rows = {m["market"]: m for m in v["comparison"]["mandis"]}
    assert rows["Nowhere"]["available"] is False
    assert v["market"]["A"]["min_price"] is not None and v["market"]["A"]["live"] is False
    assert v["comparison"]["recommendation"]["market"] in {"A", "B"}


def test_greeting_report_goodbye(client):
    lot_id, h = _auth(client)
    post = lambda stage, lang="te": client.post(  # noqa: E731
        f"/api/v1/mobile/lots/{lot_id}/advisory", json={"stage": stage, "language": lang}, headers=h).json()["data"]
    g = post("greeting")
    assert g["script"].startswith("బాబాయ్... శుభోదయం! నేను రైతన్నను మాట్లాడుతున్నాను.")
    assert "మీ ఉల్లిపాయ పంట ధరలు" in g["script"] and "టమాటా" not in g["script"]
    assert "Test Farmer" not in g["script"]
    assert g["audio"] is None and g["tts_error"]["code"] == "not_configured"  # text still returned
    assert "Onion" in post("greeting", "en")["script"]

    r = post("report")
    v = client.get(f"/api/v1/mobile/lots/{lot_id}", headers=h).json()["data"]
    rec = v["comparison"]["recommendation"]
    assert r["script"].startswith(S.report_intro("te")) and r["narration"] == "template"
    assert S.money(rec["option"]["net_revenue"]) in r["script"]
    assert "Nowhere మండికి సరిపడా ధరల సమాచారం లేదు" in r["script"]
    assert "చివరి నిర్ణయం మీదే బాబాయ్" in r["script"] and "Test Farmer" not in r["script"]
    assert post("goodbye")["script"] == S.goodbye("te")


class FakeTts:
    name = "fake"

    def __init__(self):
        self.calls = 0

    def voice(self, lang):
        return f"fake-{lang}"

    def synthesize(self, text, lang):
        self.calls += 1
        return b"ID3-fake-mp3"


def test_tts_cached_and_served_with_token(client, monkeypatch):
    fake = FakeTts()
    monkeypatch.setattr(tts, "provider", lambda: fake)
    lot_id, h = _auth(client)
    body = {"stage": "greeting", "language": "te"}
    a1 = client.post(f"/api/v1/mobile/lots/{lot_id}/advisory", json=body, headers=h).json()["data"]["audio"]
    a2 = client.post(f"/api/v1/mobile/lots/{lot_id}/advisory", json=body, headers=h).json()["data"]["audio"]
    assert a1 == a2 and fake.calls == 1  # identical script is not synthesized twice
    assert client.get(f"/api/v1{a1['path']}").status_code == 401
    got = client.get(f"/api/v1{a1['path']}", headers=h)
    assert got.status_code == 200 and got.content == b"ID3-fake-mp3"


def test_tts_failure_keeps_text(client, monkeypatch):
    class Broken(FakeTts):
        def synthesize(self, text, lang):
            raise tts.TtsError("Azure Speech timed out.")
    monkeypatch.setattr(tts, "provider", lambda: Broken())
    lot_id, h = _auth(client)
    d = client.post(f"/api/v1/mobile/lots/{lot_id}/advisory", json={"stage": "goodbye"}, headers=h).json()["data"]
    assert d["script"] == S.goodbye("te") and d["audio"] is None and d["tts_error"]["code"] == "tts_failed"


TEMPLATE = "బాబాయ్, నీ దగ్గర 10 క్వింటాళ్ల ఉల్లిపాయ ఉంది. A మండిలో మిగిలేది 1,17,389 రూపాయలు."


def test_narration_validation():
    ok = "బాబాయ్, మీ దగ్గర 10 క్వింటాళ్ల ఉల్లిపాయ ఉంది కదా. A మండిలో 1,17,389 రూపాయలు మిగులుతాయి."
    assert narration.validate(TEMPLATE, ok, "te", ["Test Farmer"]) is None
    assert narration.validate(TEMPLATE, ok.replace("1,17,389", "1,20,000"), "te", []) == "numbers changed"
    assert narration.validate(TEMPLATE, ok + " ఇంకా 5 రూపాయలు.", "te", []) == "numbers changed"
    assert narration.validate(TEMPLATE, ok.replace("బాబాయ్", "Test Farmer"), "te", ["Test Farmer"]) is not None
    assert narration.validate(TEMPLATE, ok + " నువ్వు ఏమంటావో", "te", []) == "invites a spoken reply"


def test_narration_fallbacks(monkeypatch):
    monkeypatch.setenv("BEDROCK_MODEL_ID", "test-model")
    get_settings.cache_clear()
    good = "బాబాయ్, మీ దగ్గర 10 క్వింటాళ్ల ఉల్లిపాయ ఉంది. A మండిలో 1,17,389 రూపాయలు మిగులుతాయి."
    monkeypatch.setattr(narration, "_invoke", lambda *a: '```json\n{"script": "%s"}\n```' % good)
    r = narration.narrate(TEMPLATE, "te", [])
    assert r["narration"] == "bedrock" and r["script"] == good
    monkeypatch.setattr(narration, "_invoke", lambda *a: (_ for _ in ()).throw(AssertionError("cached, not called")))
    assert narration.narrate(TEMPLATE, "te", [])["script"] == good  # cached by template hash

    other = TEMPLATE + " B మండి 20 కిలోమీటర్లు."
    monkeypatch.setattr(narration, "_invoke", lambda *a: '{"script": "బాబాయ్, ధర 999 రూపాయలు అనుకుంటా."}')
    r = narration.narrate(other, "te", [])
    assert r["narration"] == "template" and r["script"] == other and "numbers changed" in r["note"]

    def boom(*a):
        raise ConnectionError("no network")
    monkeypatch.setattr(narration, "_invoke", boom)
    r = narration.narrate(other + " 7", "te", [])
    assert r["narration"] == "template" and "unavailable" in r["note"]


def test_formatting_helpers():
    assert S.money(117389.4) == "1,17,389" and S.money(999) == "999" and S.money(-2500) == "2,500"
    assert S.crop_name("Paddy (Dhan)(Common)", "te") == "వరి"
    assert S.crop_name("Paddy (Dhan)(Common)", "en") == "Paddy"
    assert S.crop_name("Dragon Fruit", "te") == "Dragon Fruit"  # unknown crop keeps its name
    assert mobile_service.phone_key("+91 98480-12345") == "9848012345"
