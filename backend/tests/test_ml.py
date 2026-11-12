import numpy as np
import pandas as pd
import pytest

from app.ml import features as F
from app.ml import training
from tests.conftest import make_test_series


def _feats(df):
    obs = F.clean_observations(df)
    return F.build_features(obs, F.fit_encodings(obs))


def test_features_do_not_use_future_values():
    df = make_test_series(80)
    base = _feats(df)
    changed = df.copy()
    changed.loc[60:, "modal_price"] *= 3  # alter the future only
    after = _feats(changed)
    cols = F.NUMERIC_FEATURES
    pd.testing.assert_frame_equal(base.loc[:59, cols], after.loc[:59, cols])
    # target of row 59 *should* change (it is the next observation), features must not
    assert base.loc[59, "target"] != after.loc[59, "target"]


def test_target_requires_gap_within_limit():
    df = make_test_series(40, every_days=F.MAX_GAP_DAYS + 1)
    f = _feats(df)
    assert f["target"].isna().all()


def test_lag_alignment():
    df = make_test_series(40)
    f = _feats(df)
    p = df["modal_price"].to_numpy()
    assert f.loc[35, "lag7_ratio"] == pytest.approx(p[28] / p[35])
    assert f.loc[35, "target"] == pytest.approx(np.log(p[36] / p[35]))
    assert not f.loc[F.MIN_HISTORY - 1, "has_history"] and f.loc[F.MIN_HISTORY, "has_history"]


def test_chronological_split_has_no_overlap():
    f = _feats(make_test_series(300))
    train, val, test, b = F.chronological_split(f)
    assert train["target_date"].max() < val["target_date"].min()
    assert val["target_date"].max() < test["target_date"].min()
    assert b["validation_start"] < b["test_start"]


def test_metrics():
    m = F.price_metrics(np.array([100.0, 100, 100]), np.array([110.0, 90, 100]), np.array([105.0, 95, 100]))
    assert m["mae"] == pytest.approx(10 / 3)
    assert m["directional_accuracy"] == 1.0 and m["n_moved"] == 2
    naive = F.price_metrics(np.array([100.0, 100]), np.array([110.0, 90]), np.array([100.0, 100]))
    assert naive["directional_accuracy"] == 0.0


def test_insufficient_history_is_refused(tmp_path):
    path = tmp_path / "p.parquet"
    make_test_series(training.MIN_OBSERVATIONS - 1).to_parquet(path)
    with pytest.raises(training.InsufficientHistory):
        training.train(path, tmp_path, ("random_forest",))


def test_training_pipeline_is_reproducible(tmp_path):
    """Code-path test on TEST VALUES in a temp dir; artifacts are discarded with tmp_path."""
    df = pd.concat([make_test_series(260, market="A"), make_test_series(260, market="B")])
    path = tmp_path / "p.parquet"
    df.to_parquet(path)
    m1 = training.train(path, tmp_path / "m1", ("random_forest",))
    m2 = training.train(path, tmp_path / "m2", ("random_forest",))
    for name in m1["results"]:
        assert m1["results"][name]["test"]["mae"] == pytest.approx(m2["results"][name]["test"]["mae"])
    assert {"naive_last", "moving_average_7", "random_forest"} <= set(m1["results"])
    assert m1["training_dataset"]["sha256"] == m2["training_dataset"]["sha256"]
    assert len(m1["eligible_series"]) == 2


def test_horizon_target_is_first_observation_after_h_days():
    df = make_test_series(80, every_days=2)  # observations every 2 days
    obs = F.clean_observations(df)
    f = F.build_features(obs, F.fit_encodings(obs), horizon_days=7)
    p = df["modal_price"].to_numpy()
    # from row 40 (day 80), first obs on/after day 87 is day 88 = row 44
    assert f.loc[40, "target_price"] == pytest.approx(p[44])
    assert (f.loc[40, "target_date"] - f.loc[40, "arrival_date"]).days == 8
    assert f["target"].iloc[-3:].isna().all()  # no future observation -> no target
    # features identical to the next-observation build: horizon only changes the target
    base = F.build_features(obs, F.fit_encodings(obs))
    pd.testing.assert_frame_equal(base[F.FEATURES], f[F.FEATURES])


def test_horizon_target_respects_tolerance():
    df = make_test_series(30, every_days=11)  # gaps of 11 days > 7+3 tolerance window
    obs = F.clean_observations(df)
    f = F.build_features(obs, F.fit_encodings(obs), horizon_days=7)
    assert f["target"].isna().all()
