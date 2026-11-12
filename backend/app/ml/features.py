"""Feature engineering for next-observation modal-price forecasting.

Mandi series are irregular (holidays, no arrivals), so lags are *observation* lags, with explicit
calendar-gap features. Every feature for row t uses only rows <= t of the same series. The target
is log(p[t+1] / p[t]) and exists only when the next observation is at most MAX_GAP_DAYS later.
See DECISIONS.md ADR-013.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SERIES_KEYS = ["state", "district", "market", "commodity", "variety", "grade"]
LAGS = (1, 3, 7, 14, 30)
ROLL_WINDOWS = (7, 14)
MAX_GAP_DAYS = 7
HORIZONS = (7, 14, 30)  # calendar-day horizons for the storage planner (ADR-023)
HORIZON_TOLERANCE_DAYS = 3  # target = first observation within [t+h, t+h+3]; markets skip days
MIN_HISTORY = max(LAGS)  # rows with fewer prior observations get no features

NUMERIC_FEATURES = [
    *[f"lag{k}_ratio" for k in LAGS],
    *[f"roll_mean{w}_ratio" for w in ROLL_WINDOWS],
    "roll_std7_rel",
    "change_7obs",
    "spread_rel",
    "days_since_prev",
    "days_span_7obs",
    "month_sin",
    "month_cos",
    "dow",
    "log_price",
]
CATEGORICAL_FEATURES = ["commodity_id", "market_id", "variety_id"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def series_key(row: pd.Series | dict) -> tuple[str, ...]:
    return tuple(str(row[k]) for k in SERIES_KEYS)


def clean_observations(prices: pd.DataFrame) -> pd.DataFrame:
    """Rows usable for modelling: no quality flags. Sorted per series by date."""
    df = prices[prices["quality_flags"].fillna("") == ""].copy()
    df["arrival_date"] = pd.to_datetime(df["arrival_date"])
    for k in SERIES_KEYS:
        df[k] = df[k].fillna("").astype(str)
    return df.sort_values(SERIES_KEYS + ["arrival_date"]).reset_index(drop=True)


def build_features(
    obs: pd.DataFrame, encodings: dict[str, dict[str, int]], horizon_days: int | None = None
) -> pd.DataFrame:
    """Compute features (and target where available) for every observation row.

    `obs` must come from `clean_observations`. Output keeps SERIES_KEYS, arrival_date, modal_price,
    target_date, target_price and target (log return; NaN when not available).
    """
    out = []
    for _, g in obs.groupby(SERIES_KEYS, sort=False):
        g = g.sort_values("arrival_date").reset_index(drop=True)
        p = g["modal_price"].astype(float)
        d = g["arrival_date"]
        f = pd.DataFrame(index=g.index)
        for k in LAGS:
            f[f"lag{k}_ratio"] = p.shift(k) / p
        for w in ROLL_WINDOWS:
            f[f"roll_mean{w}_ratio"] = p.rolling(w, min_periods=w).mean() / p
        f["roll_std7_rel"] = p.rolling(7, min_periods=7).std() / p
        f["change_7obs"] = p / p.shift(7) - 1
        f["spread_rel"] = (g["max_price"].astype(float) - g["min_price"].astype(float)) / p
        f["days_since_prev"] = (d - d.shift(1)).dt.days
        f["days_span_7obs"] = (d - d.shift(7)).dt.days
        f["month_sin"] = np.sin(2 * np.pi * d.dt.month / 12)
        f["month_cos"] = np.cos(2 * np.pi * d.dt.month / 12)
        f["dow"] = d.dt.dayofweek
        f["log_price"] = np.log(p)
        f["commodity_id"] = encodings["commodity"].get(g["commodity"].iat[0], -1)
        f["market_id"] = encodings["market"].get(f"{g['state'].iat[0]}|{g['market'].iat[0]}", -1)
        f["variety_id"] = encodings["variety"].get(f"{g['commodity'].iat[0]}|{g['variety'].iat[0]}", -1)

        if horizon_days is None:
            next_p = p.shift(-1)
            next_d = d.shift(-1)
            gap = (next_d - d).dt.days
            valid_target = gap.notna() & (gap <= MAX_GAP_DAYS)
        else:
            dv = d.to_numpy()
            idx = np.searchsorted(dv, dv + np.timedelta64(horizon_days, "D"))
            found = idx < len(dv)
            safe = np.minimum(idx, len(dv) - 1)
            next_p = pd.Series(p.to_numpy()[safe], index=g.index)
            next_d = pd.Series(dv[safe], index=g.index)
            gap = (next_d - d).dt.days
            valid_target = pd.Series(found, index=g.index) & (gap <= horizon_days + HORIZON_TOLERANCE_DAYS)
        f["target_date"] = next_d.where(valid_target)
        f["target_price"] = next_p.where(valid_target)
        f["target"] = np.log(next_p / p).where(valid_target)

        f["has_history"] = g.index >= MIN_HISTORY
        for k in SERIES_KEYS:
            f[k] = g[k]
        f["arrival_date"] = d
        f["modal_price"] = p
        out.append(f)
    if not out:
        return pd.DataFrame(columns=[*FEATURES, *SERIES_KEYS, "arrival_date", "modal_price", "target"])
    return pd.concat(out, ignore_index=True)


def fit_encodings(obs: pd.DataFrame) -> dict[str, dict[str, int]]:
    def enc(values: pd.Series) -> dict[str, int]:
        return {v: i for i, v in enumerate(sorted(values.unique()))}

    return {
        "commodity": enc(obs["commodity"]),
        "market": enc(obs["state"] + "|" + obs["market"]),
        "variety": enc(obs["commodity"] + "|" + obs["variety"]),
    }


def chronological_split(
    feats: pd.DataFrame, val_frac: float = 0.15, test_frac: float = 0.15
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, str]]:
    """Split labelled rows by *target date* so no training target lies after any validation/test target."""
    rows = feats[feats["has_history"] & feats["target"].notna()].copy()
    if rows.empty:
        raise ValueError("no labelled rows to split")
    dates = np.sort(rows["target_date"].unique())
    val_start = dates[int(len(dates) * (1 - val_frac - test_frac))]
    test_start = dates[int(len(dates) * (1 - test_frac))]
    train = rows[rows["target_date"] < val_start]
    val = rows[(rows["target_date"] >= val_start) & (rows["target_date"] < test_start)]
    test = rows[rows["target_date"] >= test_start]
    bounds = {
        "train_start": str(pd.Timestamp(rows["target_date"].min()).date()),
        "validation_start": str(pd.Timestamp(val_start).date()),
        "test_start": str(pd.Timestamp(test_start).date()),
        "test_end": str(pd.Timestamp(rows["target_date"].max()).date()),
    }
    return train, val, test, bounds


def price_metrics(last: np.ndarray, actual: np.ndarray, predicted: np.ndarray) -> dict[str, float | int | None]:
    """MAE/RMSE in INR/quintal, MAPE (%) and directional accuracy on rows where the price moved."""
    err = predicted - actual
    moved = actual != last
    direction = (
        float(np.mean(np.sign(predicted[moved] - last[moved]) == np.sign(actual[moved] - last[moved])))
        if moved.any()
        else None
    )
    positive = actual > 0
    return {
        "n": int(len(actual)),
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(err**2))),
        "mape": float(np.mean(np.abs(err[positive] / actual[positive])) * 100) if positive.any() else None,
        "directional_accuracy": direction,
        "n_moved": int(moved.sum()),
    }
