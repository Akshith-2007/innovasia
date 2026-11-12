"""Model registry on disk: models/price_model/<version>/{model.joblib,metadata.json} + models/current.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MODEL_DIR_NAME = "price_model"
POINTER = "current.json"


def write_current_pointer(models_dir: Path, version: str) -> None:
    (models_dir / POINTER).write_text(json.dumps({"model_version": version}, indent=2), encoding="utf-8")


def current_version(models_dir: Path) -> str | None:
    p = models_dir / POINTER
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8")).get("model_version")


def model_dir(models_dir: Path, version: str) -> Path:
    return models_dir / MODEL_DIR_NAME / version


def read_metadata(models_dir: Path, version: str) -> dict[str, Any]:
    return json.loads((model_dir(models_dir, version) / "metadata.json").read_text(encoding="utf-8"))
