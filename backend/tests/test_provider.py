import json
from pathlib import Path

import httpx
import pytest

from app.core.config import get_settings
from app.core.exceptions import NotConfiguredError, UpstreamError
from app.providers.agmarknet import normalise_key, normalise_record, parse_arrival_date, parse_price
from app.providers.data_gov import DataGovClient

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "ogd_envelope_shape.json").read_text())


@pytest.fixture
def keyed(monkeypatch):
    monkeypatch.setenv("DATA_GOV_API_KEY", "test-key")
    get_settings.cache_clear()
    return get_settings()


def client_for(handler, settings) -> DataGovClient:
    return DataGovClient(settings, transport=httpx.MockTransport(handler), backoff_seconds=0)


def test_requires_api_key():
    with pytest.raises(NotConfiguredError):
        DataGovClient().fetch_page("x")


def test_pagination_walks_until_total(keyed):
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        offset = int(req.url.params["offset"])
        calls.append(offset)
        assert req.url.params["api-key"] == "test-key"
        body = dict(FIXTURE)
        body["records"] = FIXTURE["records"] if offset == 0 else FIXTURE["records"][:1]
        return httpx.Response(200, json=body)

    with client_for(handler, keyed) as c:
        pages = list(c.iter_pages("res", limit=2, pause_seconds=0))
    assert calls == [0, 2]
    assert sum(len(p.records) for p in pages) == 3
    assert "api-key" not in pages[0].request_params
    assert pages[0].raw_bytes  # exact bytes kept for the raw store


@pytest.mark.parametrize(
    "status,kind", [(401, "auth"), (403, "auth"), (429, "rate_limited"), (503, "server_error"), (404, "http_error")]
)
def test_http_errors_map_to_kinds(keyed, status, kind):
    with client_for(lambda r: httpx.Response(status), keyed) as c:
        with pytest.raises(UpstreamError) as e:
            c.fetch_page("res")
    assert e.value.kind == kind


def test_rate_limit_retries_then_succeeds(keyed):
    n = {"i": 0}

    def handler(req):
        n["i"] += 1
        return httpx.Response(429) if n["i"] < 3 else httpx.Response(200, json=FIXTURE)

    with client_for(handler, keyed) as c:
        assert len(c.fetch_page("res").records) == 2
    assert n["i"] == 3


def test_timeout(keyed):
    def handler(req):
        raise httpx.ReadTimeout("slow", request=req)

    with client_for(handler, keyed) as c:
        with pytest.raises(UpstreamError) as e:
            c.fetch_page("res")
    assert e.value.kind == "timeout"


def test_schema_change_and_invalid_json(keyed):
    with client_for(lambda r: httpx.Response(200, json={"status": "ok", "rows": []}), keyed) as c:
        with pytest.raises(UpstreamError) as e:
            c.fetch_page("res")
    assert e.value.kind == "schema_change"
    with client_for(lambda r: httpx.Response(200, text="<html>"), keyed) as c:
        with pytest.raises(UpstreamError) as e:
            c.fetch_page("res")
    assert e.value.kind == "invalid_response"


def test_api_level_error_status(keyed):
    with client_for(lambda r: httpx.Response(200, json={"status": "error", "message": "Invalid key"}), keyed) as c:
        with pytest.raises(UpstreamError) as e:
            c.fetch_page("res")
    assert e.value.kind == "auth"


def test_normalisation():
    assert normalise_key("Modal_x0020_Price") == "modal_price"
    assert normalise_key("Arrival_Date") == "arrival_date"
    assert str(parse_arrival_date("05/03/2024")) == "2024-03-05"
    assert str(parse_arrival_date("2024-03-05")) == "2024-03-05"
    assert parse_arrival_date("garbage") is None
    assert parse_price("1,250") == 1250.0
    assert parse_price("NA") is None and parse_price("") is None
    rec = normalise_record({"State": " A  B ", "Modal_x0020_Price": "10", "Arrival_Date": "01/02/2024"})
    assert rec["state"] == "A B" and rec["modal_price"] == 10.0 and rec["min_price"] is None
    assert rec["price_unit"] == "INR/quintal"


def test_api_key_never_logged_or_returned(keyed, caplog):
    import logging

    from app.core.exceptions import redact
    from app.core.logging import configure_logging

    configure_logging()
    caplog.set_level(logging.INFO)
    with client_for(lambda r: httpx.Response(200, json=FIXTURE), keyed) as c:
        c.fetch_page("res")
    assert "test-key" not in caplog.text
    assert redact("GET https://x/y?api-key=SECRET123&format=json") == "GET https://x/y?api-key=[REDACTED]&format=json"
    assert "SECRET" not in UpstreamError("failed url ?api-key=SECRET", kind="network").message


def test_security_headers():
    from fastapi.testclient import TestClient

    from app.main import app

    r = TestClient(app).get("/api/v1/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
