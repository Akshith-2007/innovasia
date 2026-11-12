"""Produce a forecast for one mandi series from the saved model. Never substitutes another series."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd

from app.core.exceptions import AmbiguousSeriesError, InsufficientDataError, NotFoundError
from app.ml import features as F
from app.ml.model_loader import LoadedModel, get_model
from app.services import data_service


def resolve_series(prices: pd.DataFrame, query: dict[str, str | None]) -> tuple[str, ...]:
    """Find exactly one series for the query; missing optional parts must be unambiguous."""
    df = prices
    for k in F.SERIES_KEYS:
        v = query.get(k)
        if v is not None:
            df = df[df[k].fillna("").str.casefold() == v.casefold()]
    if df.empty:
        raise NotFoundError("No official observations exist for this market and commodity selection.", query)
    keys = df[F.SERIES_KEYS].fillna("").drop_duplicates()
    if len(keys) > 1:
        raise AmbiguousSeriesError(
            "This commodity has several varieties or grades at this mandi. Choose one in 'Variety / grade'.",
            {"options": keys.head(25).to_dict(orient="records")},
        )
    return tuple(str(x) for x in keys.iloc[0])


def _series_row(prices: pd.DataFrame, key: tuple[str, ...], encodings: dict) -> tuple[pd.DataFrame, int]:
    """Latest feature row for one series. Filters to the series before cleaning (fast on large data)."""
    mask = np.ones(len(prices), dtype=bool)
    for k, v in zip(F.SERIES_KEYS, key):
        mask &= (prices[k].fillna("").astype(str) == v).to_numpy()
    obs = F.clean_observations(prices[mask])
    if len(obs) <= F.MIN_HISTORY:
        return obs.iloc[0:0], len(obs)
    return F.build_features(obs, encodings).iloc[[-1]], len(obs)


def _predict_return(estimator: Any | None, selected: str, row: pd.DataFrame) -> float:
    if estimator is not None:
        return float(estimator.predict(row[F.FEATURES])[0])
    if selected == "moving_average_7":
        return float(np.log(row["roll_mean7_ratio"].iat[0]))
    return 0.0  # naive_last baseline


def _interval(iv: dict, last_price: float, pred_return: float) -> dict | None:
    if not iv.get("calibrated"):
        return None
    lo, hi = iv["log_return_quantiles"]
    return {
        "level": iv["level"],
        "lower": last_price * float(np.exp(pred_return + lo)),
        "upper": last_price * float(np.exp(pred_return + hi)),
        "test_coverage": iv["test_coverage"],
    }


def _series_metrics(per_series: list[dict], key: tuple[str, ...]) -> dict | None:
    return next((s for s in per_series if tuple(str(s[k]) for k in F.SERIES_KEYS) == key), None)


def _prepare(query: dict[str, str | None], model: LoadedModel) -> tuple[tuple[str, ...], dict, pd.DataFrame]:
    prices = data_service.market_prices()
    key = resolve_series(prices, query)
    series = dict(zip(F.SERIES_KEYS, key))
    row, n = _series_row(prices, key, model.metadata["encodings"])
    if key not in model.eligible_keys:
        raise InsufficientDataError(
            "This series did not have enough history to be included in model training, so no forecast is produced.",
            {"series": series, "clean_observations": n, "required": model.metadata["config"]["min_observations"]},
        )
    if row.empty or row[F.FEATURES].isna().any(axis=None):
        raise InsufficientDataError("Latest observation lacks complete feature history.", {"series": series})
    return key, series, row


def predict(query: dict[str, str | None], model: LoadedModel | None = None) -> dict[str, Any]:
    model = model or get_model()
    meta = model.metadata
    key, series, row = _prepare(query, model)

    last_price = float(row["modal_price"].iat[0])
    latest_date = pd.Timestamp(row["arrival_date"].iat[0]).date()
    pred_return = _predict_return(model.estimator, meta["selected_model"], row)
    interval = _interval(meta.get("interval") or {}, last_price, pred_return)
    days_old = (date.today() - latest_date).days
    return {
        "series": series,
        "latest_observation": {"date": str(latest_date), "modal_price": last_price},
        "prediction": {
            "modal_price": round(last_price * float(np.exp(pred_return)), 2),
            "unit": "INR/quintal",
            "horizon": "next reported observation (within 7 days of the latest observation)",
            "interval": interval,
            "interval_unavailable_reason": None
            if interval
            else "Prediction interval failed calibration on the test period, so none is shown.",
        },
        "model": {
            "version": model.version,
            "selected_model": meta["selected_model"],
            "trained_at": meta["trained_at"],
            "data_cutoff": meta["data_cutoff"],
            "test_metrics_overall": meta["results"][meta["selected_model"]]["test"],
            "test_metrics_series": _series_metrics(meta.get("per_series_test", []), key),
        },
        "warnings": [f"Latest observation for this series is {days_old} days old; the forecast is for the next market day after it, not for today."] if days_old > 7 else [],
    }


def _horizons(model: LoadedModel, key: tuple[str, ...], row: pd.DataFrame) -> list[dict[str, Any]]:
    last_price = float(row["modal_price"].iat[0])
    latest_date = pd.Timestamp(row["arrival_date"].iat[0]).date()
    out = []
    for h_str, hm in sorted((model.metadata.get("horizons") or {}).items(), key=lambda kv: int(kv[0])):
        h = int(h_str)
        if not hm.get("available"):
            out.append({"horizon_days": h, "available": False, "reason": hm.get("reason")})
            continue
        r = _predict_return(model.horizon_estimators.get(h), hm["selected_model"], row)
        out.append({
            "horizon_days": h,
            "available": True,
            "target_date_window": [str(latest_date + timedelta(days=h)),
                                   str(latest_date + timedelta(days=h + hm["tolerance_days"]))],
            "modal_price": round(last_price * float(np.exp(r)), 2),
            "interval": _interval(hm.get("interval") or {}, last_price, r),
            "selected_model": hm["selected_model"],
            "beats_naive_on_test": hm["beats_naive_on_test"],
            "test_metrics_overall": hm["results"][hm["selected_model"]]["test"],
            "naive_test_metrics_overall": hm["results"]["naive_last"]["test"],
            "test_metrics_series": _series_metrics(hm.get("per_series_test", []), key),
        })
    return out


def forecast_horizons(query: dict[str, str | None], model: LoadedModel | None = None) -> dict[str, Any]:
    """Price expected 7/14/30 days after the latest observation, with each horizon's own test record."""
    model = model or get_model()
    key, series, row = _prepare(query, model)
    return {
        "series": series,
        "latest_observation": {"date": str(pd.Timestamp(row["arrival_date"].iat[0]).date()),
                               "modal_price": float(row["modal_price"].iat[0])},
        "horizons": _horizons(model, key, row),
        "model_version": model.version,
        "data_cutoff": model.metadata["data_cutoff"],
    }
