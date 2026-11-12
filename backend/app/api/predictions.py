from fastapi import APIRouter

from app.ml import predictor
from app.ml.model_loader import get_model
from app.schemas.common import Envelope, PredictRequest
from app.services import market_service

router = APIRouter(prefix="/ml", tags=["machine learning"])

_INFO_KEYS = (
    "model_version", "task", "forecast_horizon", "max_gap_days", "trained_at", "data_cutoff",
    "training_dataset", "split", "split_rows", "selected_model", "selected_is_baseline",
    "selection_rule", "feature_schema", "config", "interval",
)


@router.get("/model-info", response_model=Envelope[dict])
def model_info():
    meta = get_model().metadata
    info = {k: meta.get(k) for k in _INFO_KEYS}
    info["eligible_series_count"] = len(meta.get("eligible_series", []))
    info["eligible_series"] = meta.get("eligible_series", [])
    return Envelope(data=info)


@router.get("/metrics", response_model=Envelope[dict])
def metrics():
    meta = get_model().metadata
    return Envelope(
        data={
            "model_version": meta["model_version"],
            "selected_model": meta["selected_model"],
            "split": meta["split"],
            "split_rows": meta["split_rows"],
            "results": meta["results"],
            "per_series_test": meta["per_series_test"],
            "interval": meta["interval"],
        },
        meta={"units": {"mae": "INR/quintal", "rmse": "INR/quintal", "mape": "percent"}},
    )


@router.post("/predict", response_model=Envelope[dict])
def predict(req: PredictRequest):
    result = predictor.predict(req.model_dump())
    return Envelope(data=result, source=market_service.local_source())
