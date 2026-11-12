"""Test isolation: every test gets empty temp data/models dirs and no API key.

Inputs built in tests are TEST VALUES that exercise code paths. They are never written to
backend/data or backend/models, never shown on the website and never used to ship a model.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from app.core.config import get_settings
from app.ml import model_loader


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("MODELS_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("DATA_GOV_API_KEY", "")
    monkeypatch.setenv("ADMIN_PASSWORD", "")
    monkeypatch.setenv("DEVICE_KEY", "")
    # Never reach real Bedrock / Azure from tests (backend/.env may configure them).
    monkeypatch.setenv("BEDROCK_MODEL_ID", "")
    monkeypatch.setenv("AZURE_SPEECH_KEY", "")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "")
    monkeypatch.setenv("MOBILE_LINK_SECRET", "")
    (tmp_path / "models").mkdir()
    get_settings.cache_clear()
    model_loader._load.cache_clear()
    yield get_settings()
    get_settings.cache_clear()
    model_loader._load.cache_clear()


def make_test_series(n: int, market: str = "Test Market A", commodity: str = "Test Commodity",
                     start: date = date(2020, 1, 1), every_days: int = 1) -> pd.DataFrame:
    """Deterministic TEST VALUES in the processed-parquet schema (not market data)."""
    rows = []
    for i in range(n):
        p = 1000.0 + 7.0 * (i % 11) + 0.5 * i
        rows.append({
            "state": "Test State", "district": "Test District", "market": market,
            "commodity": commodity, "variety": "Other", "grade": "FAQ",
            "arrival_date": start + timedelta(days=i * every_days),
            "min_price": p - 50, "max_price": p + 50, "modal_price": p,
            "price_unit": "INR/quintal", "quality_flags": "",
            "source_resource_id": "test", "source_run_id": "test", "retrieved_at": "2020-01-01T00:00:00+00:00",
        })
    return pd.DataFrame(rows)
