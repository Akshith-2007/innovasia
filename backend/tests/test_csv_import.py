"""CSV import path (ADR-019). Files here are TEST VALUES in temp dirs, not market data."""

import pytest

from app.pipeline import market_processing, raw_store
from scripts import fetch_official_data

HEADER = "State,District Name,Market Name,Commodity,Variety,Grade,Min Price (Rs./Quintal),Max Price (Rs./Quintal),Modal Price (Rs./Quintal),Price Date\n"


def _csv(tmp_path, body, header=HEADER, name="export.csv"):
    p = tmp_path / name
    p.write_text(header + body, encoding="utf-8")
    return p


def test_market_csv_import_end_to_end(tmp_path):
    f = _csv(tmp_path, "TS,TD,TM,TC,TV,FAQ,90,110,100,01 Jan 2024\nTS,TD,TM,TC,TV,FAQ,95,115,105,02-Jan-2024\n")
    rc = fetch_official_data.main(["market-import", str(f), "--url", "https://example.invalid/test"])
    assert rc == 0
    runs = raw_store.list_runs("agmarknet")
    assert len(runs) == 1
    run_dir, manifest = runs[0]
    assert manifest["kind"] == "file_import" and manifest["record_count"] == 2
    assert raw_store.verify_run(run_dir, manifest) == []
    frame, report = market_processing.load_raw_frame(runs)
    df, _ = market_processing.validate_and_clean(frame)
    assert list(df["modal_price"]) == [100.0, 105.0]
    assert [str(d) for d in df["arrival_date"]] == ["2024-01-01", "2024-01-02"]
    assert report["runs"][manifest["run_id"]]["missing_canonical_fields"] == []


def test_refuses_per_kg_prices(tmp_path):
    f = _csv(tmp_path, "TS,TM,TC,1,01/01/2024\n", header="State,Market,Commodity,Modal Price (Rs./Kg),Arrival_Date\n")
    with pytest.raises(SystemExit, match="Rs./quintal"):
        fetch_official_data.main(["market-import", str(f), "--url", "x"])
    assert raw_store.list_runs("agmarknet") == []


def test_refuses_missing_columns(tmp_path):
    f = _csv(tmp_path, "TS,TC,100\n", header="State,Commodity,Modal Price\n")
    with pytest.raises(SystemExit, match="missing required columns"):
        fetch_official_data.main(["market-import", str(f), "--url", "x"])
