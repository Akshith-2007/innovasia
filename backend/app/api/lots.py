"""Admin-only farmer lots and best-mandi comparison (ADR-026)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.device import require_admin
from app.schemas.common import Envelope
from app.services import lot_service, market_service

router = APIRouter(prefix="/admin/lots", tags=["farmer lots"], dependencies=[Depends(require_admin)])


class CandidateMandi(BaseModel):
    market: str = Field(min_length=1, max_length=120)
    district: str | None = Field(None, max_length=120)
    state: str | None = Field(None, max_length=80, description="Defaults to the lot's state")
    distance_km: float = Field(ge=0, le=2_000, description="Road distance from the lot to this mandi")


class LotIn(BaseModel):
    farmer_name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=5, max_length=20, pattern=r"^\+?[0-9 -]+$")
    village: str | None = Field(None, max_length=120)
    state: str = Field(min_length=1, max_length=80)
    district: str | None = Field(None, max_length=120)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    commodity: str = Field(min_length=1, max_length=120)
    variety: str | None = None
    grade: str | None = None
    quantity_quintals: float = Field(gt=0, le=100_000)
    total_cost: float | None = Field(None, ge=0, description="Total cost of production for this lot (INR)")
    transport_rate_per_quintal_km: float = Field(ge=0, le=1_000, description="Fare, INR per quintal per km")
    market_fee_pct: float | None = Field(None, ge=0, le=50)
    storage_option: str = "sell_now"
    storage_cost_per_quintal_per_month: float | None = Field(None, ge=0, le=100_000)
    loss_pct_per_30_days: float | None = Field(None, ge=0, le=100)
    max_storage_days: int | None = Field(None, ge=0, le=730)
    mandis: list[CandidateMandi] = Field(min_length=1, max_length=20)


@router.get("", response_model=Envelope[list[dict]])
def list_lots():
    return Envelope(data=lot_service.list_lots())


@router.post("", response_model=Envelope[dict], status_code=201)
def add_lot(lot: LotIn):
    return Envelope(data=lot_service.add_lot(lot.model_dump()))


@router.delete("/{lot_id}", response_model=Envelope[dict])
def delete_lot(lot_id: str):
    lot_service.delete_lot(lot_id)
    return Envelope(data={"deleted": lot_id})


@router.get("/{lot_id}/compare", response_model=Envelope[dict])
def compare(lot_id: str):
    return Envelope(data=lot_service.compare(lot_id), source=market_service.local_source())
