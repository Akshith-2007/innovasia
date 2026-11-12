"""Kaggle mirror path (ADR-022). Parquet files here are TEST VALUES in temp dirs, not market data."""

import pandas as pd
import pytest

from app.pipeline import market_processing, raw_store
from app.services import market_service
from scripts import import_kaggle_mirror


def _mirror_parquet(dir_, year=2024, rows=None):
    rows = rows or [
        ("Telangana", "TD", "TM", "TC", "TV", "FAQ", f"{year}-01-01", 90.0, 110.0, 100.0, 1),
        ("Telangana", "TD", "TM", "TC", "TV", "FAQ", f"{year}-01-02", 0.0, 0.0, 0.0, 1),
        ("Kerala", "KD", "KM", "TC", "TV", "FAQ", f"{year}-01-01", 1.0, 3.0, 2.0, 1),
    ]
    df = pd.DataFrame(rows, columns=["State", "District", "Market", "Commodity", "Variety", "Grade",
                                     "Arrival_Date", "Min_Price", "Max_Price", "Modal_Price", "Commodity_Code"])
    path = dir_ / f"{year}.parquet"
    df.to_parquet(path, index=False)
    return path


def test_import_labels_mirror_and_scope(tmp_path):
    _mirror_parquet(tmp_path)
    assert import_kaggle_mirror.main(["--years", "2024", "--from-dir", str(tmp_path)]) == 0
    runs = raw_store.list_runs("agmarknet")
    (run_dir, manifest), = runs
    assert manifest["source_kind"] == "third_party_mirror"
    assert "GODL" in manifest["licence"] and manifest["record_count"] == 3
    assert raw_store.verify_run(run_dir, manifest) == []

    frame, report = market_processing.load_raw_frame(runs, ["Telangana"])
    assert set(frame["state"]) == {"Telangana"}
    df, q = market_processing.validate_and_clean(frame)
    assert list(df["modal_price"]) == [100.0]  # zero price excluded, Kerala out of scope
    assert q["rows_by_source_kind"] == {"third_party_mirror": 1}

    # Re-import of the same year is refused (raw runs are immutable).
    import_kaggle_mirror.main(["--years", "2024", "--from-dir", str(tmp_path)])
    assert len(raw_store.list_runs("agmarknet")) == 1


def test_official_rows_beat_mirror_rows():
    base = {"state": "S", "district": "D", "market": "M", "commodity": "C", "variety": "V", "grade": "FAQ",
            "arrival_date": pd.Timestamp("2024-01-01").date(), "min_price": 90.0, "max_price": 110.0,
            "price_unit": "INR/quintal", "source_resource_id": "r"}
    frame = pd.DataFrame([
        {**base, "modal_price": 100.0, "source_kind": "official", "source_run_id": "a", "retrieved_at": "2024-01-01"},
        {**base, "modal_price": 105.0, "source_kind": "third_party_mirror", "source_run_id": "b", "retrieved_at": "2025-01-01"},
    ])
    df, _ = market_processing.validate_and_clean(frame)
    assert len(df) == 1 and df["modal_price"].iat[0] == 100.0 and df["source_kind"].iat[0] == "official"


def test_source_info_discloses_mirror():
    df = pd.DataFrame({"arrival_date": ["2024-01-01"], "source_kind": ["third_party_mirror"]})
    info = market_service.local_source(df)
    assert info.third_party is True and "Kaggle" in info.name and "not directly from data.gov.in" in info.note
    official = market_service.local_source(pd.DataFrame({"arrival_date": ["2024-01-01"], "source_kind": ["official"]}))
    assert official.third_party is False and "Kaggle" not in official.name


def test_rejects_non_parquet(tmp_path):
    (tmp_path / "2024.parquet").write_text("not parquet")
    with pytest.raises(SystemExit, match="not a Parquet"):
        import_kaggle_mirror.main(["--years", "2024", "--from-dir", str(tmp_path)])
