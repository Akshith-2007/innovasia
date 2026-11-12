"""Loads the current trained model artifact once and caches it in-process."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import joblib

from app.core.config import get_settings
from app.core.exceptions import ModelUnavailableError
from app.ml.metadata import current_version, model_dir, read_metadata


@dataclass(frozen=True)
class LoadedModel:
    version: str
    metadata: dict[str, Any]
    estimator: Any | None  # None when a baseline won selection
    horizon_estimators: dict[int, Any]  # calendar-horizon models (ADR-023); empty for older artifacts

    @property
    def eligible_keys(self) -> set[tuple[str, ...]]:
        from app.ml.features import SERIES_KEYS

        return {tuple(str(s[k]) for k in SERIES_KEYS) for s in self.metadata["eligible_series"]}


@lru_cache
def _load(version: str) -> LoadedModel:
    settings = get_settings()
    meta = read_metadata(settings.models_dir, version)
    estimator = None
    if meta.get("model_file"):
        estimator = joblib.load(model_dir(settings.models_dir, version) / meta["model_file"])
    horizon_estimators = {
        int(h): joblib.load(model_dir(settings.models_dir, version) / hm["model_file"])
        for h, hm in (meta.get("horizons") or {}).items()
        if hm.get("available") and hm.get("model_file")
    }
    return LoadedModel(version=version, metadata=meta, estimator=estimator, horizon_estimators=horizon_estimators)


def get_model() -> LoadedModel:
    version = current_version(get_settings().models_dir)
    if not version:
        raise ModelUnavailableError(
            "No trained model is available yet. Run `python -m scripts.train_price_model` after fetching data."
        )
    try:
        return _load(version)
    except FileNotFoundError as exc:
        raise ModelUnavailableError(f"Model artifact for version {version} is missing: {exc}") from exc


def model_available() -> bool:
    try:
        get_model()
        return True
    except ModelUnavailableError:
        return False
