import json
import os
import stat
from datetime import date

import pandas as pd
import pytest

from app.pipeline import market_processing, raw_store
from app.providers.data_gov import ResourcePage


def _page(records, offset=0):
    body = {"status": "ok", "total": len(records), "records": records, "field": []}
    raw = json.dumps(body).encode()
    return ResourcePage("res", offset, 1000, len(records), records, [], "t", ["o"], None,
                        "2024-01-01T00:00:00+00:00", body, raw, {"offset": offset})


def _rec(market="M", date_="01/01/2024", modal="100", mn="90", mx="110", **kw):
    return {"state": "S", "district": "D", "market": market, "commodity": "C", "variety": "V", "grade": "FAQ",
            "arrival_date": date_, "min_price": mn, "max_price": mx, "modal_price": modal, **kw}


def test_raw_store_is_write_once_and_verifiable():
    s = raw_store.store_api_pages("agmarknet", "t", "src", "res", "url", {}, [_page([_rec()])])
    runs = raw_store.list_runs("agmarknet")
    assert len(runs) == 1
    run_dir, manifest = runs[0]
    assert manifest["record_count"] == 1 and manifest["complete"]
    assert raw_store.verify_run(run_dir, manifest) == []
    page = run_dir / "page_0001.json"
    assert not os.stat(page).st_mode & stat.S_IWRITE
    with pytest.raises(FileExistsError):
        raw_store._write_once(page, b"x")
    os.chmod(page, stat.S_IWRITE | stat.S_IREAD)
    page.write_bytes(b"tampered")
    assert raw_store.verify_run(run_dir, manifest) == ["checksum mismatch page_0001.json"]
    assert s.record_count == 1


def test_validation_excludes_without_filling():
    recs = [
        _rec(market="ok"),
        _rec(market="nomodal", modal="NA"),
        _rec(market="zero", modal="0"),
        _rec(market="nodate", date_="??"),
        _rec(market="swap", mn="120", mx="80"),
        _rec(market="ok"),  # exact duplicate
    ]
    raw_store.store_api_pages("agmarknet", "t", "src", "res", "url", {}, [_page(recs)])
    frame, _ = market_processing.load_raw_frame(raw_store.list_runs("agmarknet"))
    df, report = market_processing.validate_and_clean(frame)
    assert set(df["market"]) == {"ok", "swap"}
    assert report["excluded"]["missing_or_non_numeric_modal_price"] == 1
    assert report["excluded"]["non_positive_modal_price"] == 1
    assert report["excluded"]["missing_or_unparseable_arrival_date"] == 1
    assert report["exact_duplicates_removed"] == 1
    assert "min_greater_than_max" in df.loc[df["market"] == "swap", "quality_flags"].iat[0]


def test_conflicting_duplicate_keeps_latest_retrieval():
    frame = pd.DataFrame([
        {**market_processing.normalise_record(_rec(modal="100")), "source_resource_id": "r",
         "source_run_id": "a", "retrieved_at": "2024-01-01"},
        {**market_processing.normalise_record(_rec(modal="105")), "source_resource_id": "r",
         "source_run_id": "b", "retrieved_at": "2024-02-01"},
    ])
    df, report = market_processing.validate_and_clean(frame)
    assert len(df) == 1 and df["modal_price"].iat[0] == 105
    assert report["conflicting_duplicate_groups_resolved_latest_retrieval"] == 1


def test_no_forward_fill_of_missing_dates():
    frame = pd.DataFrame([
        {**market_processing.normalise_record(_rec(date_=d)), "source_resource_id": "r",
         "source_run_id": "a", "retrieved_at": "x"}
        for d in ("01/01/2024", "05/01/2024")
    ])
    df, _ = market_processing.validate_and_clean(frame)
    assert sorted(df["arrival_date"]) == [date(2024, 1, 1), date(2024, 1, 5)]
