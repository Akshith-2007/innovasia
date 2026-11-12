"""Train and compare baselines + candidate models on real AGMARKNET observations.

Called by scripts/train_price_model.py. Never invoked by the API or dev launcher.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from app.ml import features as F
from app.ml.metadata import MODEL_DIR_NAME, write_current_pointer
from app.pipeline.raw_store import sha256_file

log = logging.getLogger(__name__)

MIN_OBSERVATIONS = 120  # clean observations a series needs to be eligible (ADR-014)
MIN_SERIES_TEST_ROWS = 10  # rows needed to publish per-series test metrics
INTERVAL_LEVEL = 0.80
INTERVAL_TOLERANCE = 0.05
RANDOM_STATE = 42

CONFIG: dict[str, dict[str, Any]] = {
    "random_forest": {"n_estimators": 300, "min_samples_leaf": 5, "max_features": 0.5},
    "xgboost": {
        "n_estimators": 500,
        "learning_rate": 0.03,
        "max_depth": 6,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 5,
    },
}


class InsufficientHistory(RuntimeError):
    pass


def _make_model(name: str):
    if name == "random_forest":
        return RandomForestRegressor(random_state=RANDOM_STATE, n_jobs=-1, **CONFIG[name])
    if name == "xgboost":
        from xgboost import XGBRegressor

        return XGBRegressor(random_state=RANDOM_STATE, n_jobs=-1, **CONFIG[name])
    raise ValueError(name)


def _baseline_returns(name: str, rows: pd.DataFrame) -> np.ndarray:
    if name == "naive_last":
        return np.zeros(len(rows))
    if name == "moving_average_7":
        return np.log(rows["roll_mean7_ratio"].to_numpy())
    raise ValueError(name)


def _to_prices(rows: pd.DataFrame, pred_return: np.ndarray) -> np.ndarray:
    return rows["modal_price"].to_numpy() * np.exp(pred_return)


def _evaluate(rows: pd.DataFrame, pred_return: np.ndarray) -> dict[str, Any]:
    return F.price_metrics(
        rows["modal_price"].to_numpy(), rows["target_price"].to_numpy(), _to_prices(rows, pred_return)
    )


def assess_coverage(prices: pd.DataFrame) -> pd.DataFrame:
    obs = F.clean_observations(prices)
    g = obs.groupby(F.SERIES_KEYS)["arrival_date"]
    cov = g.agg(observations="count", first="min", last="max").reset_index()
    cov["eligible"] = cov["observations"] >= MIN_OBSERVATIONS
    return cov.sort_values("observations", ascending=False)


def _fit_and_evaluate(feats: pd.DataFrame, candidates: tuple[str, ...]) -> dict[str, Any]:
    """Chronological split, fit candidates, select on validation, refit, score once on test."""
    train_df, val_df, test_df, bounds = F.chronological_split(feats)
    for name, part in (("train", train_df), ("validation", val_df), ("test", test_df)):
        if len(part) < 50:
            raise InsufficientHistory(f"{name} split has only {len(part)} rows; need >= 50.")

    X = F.FEATURES
    results: dict[str, dict[str, Any]] = {}
    val_preds: dict[str, np.ndarray] = {}
    for name in ("naive_last", "moving_average_7"):
        val_preds[name] = _baseline_returns(name, val_df)
        results[name] = {"type": "baseline", "validation": _evaluate(val_df, val_preds[name])}
    for name in candidates:
        model = _make_model(name)
        model.fit(train_df[X], train_df["target"])
        val_preds[name] = model.predict(val_df[X])
        results[name] = {"type": "candidate", "validation": _evaluate(val_df, val_preds[name])}
        log.info("%s validation MAE %.2f", name, results[name]["validation"]["mae"])

    selected = min(results, key=lambda n: results[n]["validation"]["mae"])
    log.info("selected %s by validation MAE", selected)

    # Refit learned models on train+validation, then score everything once on the held-out test set.
    train_val = pd.concat([train_df, val_df])
    final_model = None
    test_preds: dict[str, np.ndarray] = {}
    for name in results:
        if results[name]["type"] == "baseline":
            test_preds[name] = _baseline_returns(name, test_df)
        else:
            m = _make_model(name)
            m.fit(train_val[X], train_val["target"])
            test_preds[name] = m.predict(test_df[X])
            if name == selected:
                final_model = m
        results[name]["test"] = _evaluate(test_df, test_preds[name])

    # Empirical interval from validation residuals; published only if test coverage confirms it.
    resid = val_df["target"].to_numpy() - val_preds[selected]
    q_lo, q_hi = np.quantile(resid, [(1 - INTERVAL_LEVEL) / 2, 1 - (1 - INTERVAL_LEVEL) / 2])
    sel_test = test_preds[selected]
    covered = (test_df["target"].to_numpy() >= sel_test + q_lo) & (test_df["target"].to_numpy() <= sel_test + q_hi)
    coverage_rate = float(covered.mean())
    interval = {
        "level": INTERVAL_LEVEL,
        "log_return_quantiles": [float(q_lo), float(q_hi)],
        "test_coverage": coverage_rate,
        "calibrated": abs(coverage_rate - INTERVAL_LEVEL) <= INTERVAL_TOLERANCE,
        "method": "empirical quantiles of validation residuals; accepted if test coverage within ±5 pts",
    }

    test_out = test_df[F.SERIES_KEYS + ["arrival_date", "modal_price", "target_date", "target_price"]].copy()
    for name, pr in test_preds.items():
        test_out[f"pred_{name}"] = _to_prices(test_df, pr)

    per_series = []
    for key, g in test_out.groupby(F.SERIES_KEYS):
        if len(g) < MIN_SERIES_TEST_ROWS:
            continue
        entry = dict(zip(F.SERIES_KEYS, key))
        last, actual = g["modal_price"].to_numpy(), g["target_price"].to_numpy()
        entry["selected"] = F.price_metrics(last, actual, g[f"pred_{selected}"].to_numpy())
        entry["naive_last"] = F.price_metrics(last, actual, g["pred_naive_last"].to_numpy())
        per_series.append(entry)

    return {
        "results": results, "selected": selected, "final_model": final_model, "interval": interval,
        "test_out": test_out, "per_series": per_series, "bounds": bounds,
        "split_rows": {"train": len(train_df), "validation": len(val_df), "test": len(test_df)},
    }


def train(
    prices_path: Path,
    models_dir: Path,
    candidates: tuple[str, ...] = ("random_forest", "xgboost"),
    horizon_list: tuple[int, ...] = F.HORIZONS,
    horizon_candidates: tuple[str, ...] = ("xgboost",),
) -> dict:
    prices = pd.read_parquet(prices_path)
    coverage = assess_coverage(prices)
    eligible = coverage[coverage["eligible"]]
    if eligible.empty:
        raise InsufficientHistory(
            f"No series has >= {MIN_OBSERVATIONS} clean observations. "
            f"Best series has {int(coverage['observations'].max()) if len(coverage) else 0}. "
            "Fetch more official history before training."
        )

    obs = F.clean_observations(prices)
    keyset = set(map(tuple, eligible[F.SERIES_KEYS].to_numpy()))
    obs = obs[[k in keyset for k in map(tuple, obs[F.SERIES_KEYS].to_numpy())]]
    encodings = F.fit_encodings(obs)
    feats = F.build_features(obs, encodings)
    core = _fit_and_evaluate(feats, candidates)
    results, selected, final_model = core["results"], core["selected"], core["final_model"]
    interval, test_out, per_series, bounds = core["interval"], core["test_out"], core["per_series"], core["bounds"]
    X = F.FEATURES

    # Calendar horizons for the storage planner (ADR-023). A horizon that cannot be evaluated is
    # recorded as unavailable instead of failing the whole run.
    horizons: dict[str, Any] = {}
    horizon_models: dict[int, Any] = {}
    for h in horizon_list:
        try:
            hc = _fit_and_evaluate(F.build_features(obs, encodings, horizon_days=h), horizon_candidates)
        except InsufficientHistory as exc:
            horizons[str(h)] = {"available": False, "reason": str(exc)}
            continue
        hsel = hc["selected"]
        horizons[str(h)] = {
            "available": True,
            "horizon_days": h,
            "tolerance_days": F.HORIZON_TOLERANCE_DAYS,
            "selected_model": hsel,
            "selected_is_baseline": hc["results"][hsel]["type"] == "baseline",
            "beats_naive_on_test": hc["results"][hsel]["test"]["mae"] < hc["results"]["naive_last"]["test"]["mae"],
            "model_file": f"model_h{h}.joblib" if hc["final_model"] is not None else None,
            "results": hc["results"],
            "interval": hc["interval"],
            "split": hc["bounds"],
            "split_rows": hc["split_rows"],
            "per_series_test": hc["per_series"],
        }
        horizon_models[h] = (hc["final_model"], hc["test_out"])
        log.info("horizon %sd: %s test MAE %.1f vs naive %.1f", h, hsel, hc["results"][hsel]["test"]["mae"],
                 hc["results"]["naive_last"]["test"]["mae"])

    dataset_sha = sha256_file(prices_path)
    trained_at = datetime.now(timezone.utc)
    version = f"{trained_at:%Y%m%d%H%M%S}-{dataset_sha[:8]}"
    out_dir = models_dir / MODEL_DIR_NAME / version
    out_dir.mkdir(parents=True, exist_ok=False)
    model_file = "model.joblib"
    if final_model is not None:
        joblib.dump(final_model, out_dir / model_file)
    test_out.to_parquet(out_dir / "test_predictions.parquet", index=False)
    for h, (hm, hout) in horizon_models.items():
        if hm is not None:
            joblib.dump(hm, out_dir / f"model_h{h}.joblib")
        hout.to_parquet(out_dir / f"test_predictions_h{h}.parquet", index=False)

    eligible_out = eligible.copy()
    eligible_out["first"] = eligible_out["first"].dt.date.astype(str)
    eligible_out["last"] = eligible_out["last"].dt.date.astype(str)
    metadata = {
        "model_version": version,
        "task": "next reported observation modal price (INR/quintal) for one mandi series",
        "forecast_horizon": "next_reported_observation",
        "max_gap_days": F.MAX_GAP_DAYS,
        "trained_at": trained_at.isoformat(timespec="seconds"),
        "data_cutoff": str(pd.Timestamp(obs["arrival_date"].max()).date()),
        "training_dataset": {
            "path": prices_path.name,
            "sha256": dataset_sha,
            "rows": int(len(prices)),
            "source_kinds": sorted(prices["source_kind"].dropna().unique().tolist()) if "source_kind" in prices else ["official"],
            "states": sorted(obs["state"].unique().tolist()),
        },
        "split": bounds,
        "split_rows": core["split_rows"],
        "selected_model": selected,
        "selected_is_baseline": results[selected]["type"] == "baseline",
        "model_file": model_file if final_model is not None else None,
        "selection_rule": "lowest validation MAE (INR/quintal)",
        "feature_schema": {"features": X, "categorical": F.CATEGORICAL_FEATURES, "target": "log(p[t+1]/p[t])"},
        "encodings": encodings,
        "config": {"candidates": CONFIG, "min_observations": MIN_OBSERVATIONS, "random_state": RANDOM_STATE},
        "results": results,
        "per_series_test": per_series,
        "interval": interval,
        "eligible_series": eligible_out.to_dict(orient="records"),
        "horizons": horizons,
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")
    write_current_pointer(models_dir, version)
    return metadata
