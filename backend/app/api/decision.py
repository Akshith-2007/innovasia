from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.ml import predictor
from app.schemas.common import Envelope, PredictRequest
from app.services import market_service, storage_planner

router = APIRouter(prefix="/decision", tags=["storage planner"])


class PlanRequest(BaseModel):
    state: str
    district: str | None = None
    market: str
    commodity: str
    variety: str | None = None
    grade: str | None = None
    quantity_quintals: float = Field(gt=0, le=100_000)
    total_cost: float | None = Field(None, ge=0, description="Total cost of production for this quantity (INR)")
    transport_cost_per_quintal: float | None = Field(None, ge=0, le=100_000)
    market_fee_pct: float | None = Field(None, ge=0, le=50, description="Commission + market fee, % of sale value")
    storage_option: str
    storage_cost_per_quintal_per_month: float | None = Field(None, ge=0, le=100_000)
    loss_pct_per_30_days: float | None = Field(None, ge=0, le=100)
    max_storage_days: int | None = Field(None, ge=0, le=730)


@router.get("/storage-options", response_model=Envelope[dict])
def storage_options(commodity: str):
    return Envelope(data=storage_planner.options_for(commodity))


@router.post("/forecast-horizons", response_model=Envelope[dict])
def forecast_horizons(req: PredictRequest):
    return Envelope(data=predictor.forecast_horizons(req.model_dump()), source=market_service.local_source())


@router.post("/plan", response_model=Envelope[dict])
def plan(req: PlanRequest):
    return Envelope(data=storage_planner.plan(req.model_dump()), source=market_service.local_source())
