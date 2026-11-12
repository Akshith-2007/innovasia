"""Farmer lot register and sale plans (admin password). ADR-026."""

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.device import require_admin
from app.schemas.common import Envelope
from app.services import farmer_service, geo

router = APIRouter(prefix="/admin", tags=["farmer portal"], dependencies=[Depends(require_admin)])


class Lot(BaseModel):
    farmer_name: str = Field(min_length=1, max_length=80)
    village: str = Field(min_length=1, max_length=80)
    commodity: str = Field(min_length=1, max_length=120)
    variety: str | None = Field(None, max_length=120)
    grade: str | None = Field(None, max_length=60)
    quantity_q: float = Field(gt=0, le=100_000, description="Quantity in quintals")
    entry_date: date


class FarmerSettings(BaseModel):
    storage_state: str | None = None
    storage_district: str | None = None
    transport_per_q_km: float | None = Field(None, ge=0, le=1_000, description="₹ per quintal per km")
    storage_rent_per_q_month: float | None = Field(None, ge=0, le=100_000)
    loss_pct_per_30_days: float | None = Field(None, ge=0, le=100)
    market_fee_pct: float | None = Field(None, ge=0, le=50)
    max_km: float | None = Field(None, gt=0, le=5_000)
    km_overrides: dict[str, float | None] | None = None


@router.get("/farmer/settings", response_model=Envelope[dict])
def get_settings_():
    return Envelope(data=farmer_service.get_settings_doc(), meta={"districts": geo.districts()})


@router.put("/farmer/settings", response_model=Envelope[dict])
def put_settings(change: FarmerSettings):
    return Envelope(data=farmer_service.update_settings(change.model_dump(exclude_unset=True)))


@router.get("/lots", response_model=Envelope[list[dict]])
def lots():
    return Envelope(data=farmer_service.list_lots())


@router.post("/lots", response_model=Envelope[dict])
def add_lot(lot: Lot):
    data = lot.model_dump()
    data["entry_date"] = str(data["entry_date"])
    return Envelope(data=farmer_service.add_lot(data))


@router.delete("/lots/{lot_id}", response_model=Envelope[dict])
def delete_lot(lot_id: str):
    farmer_service.delete_lot(lot_id)
    return Envelope(data={"deleted": lot_id})


@router.get("/lots/{lot_id}/plan", response_model=Envelope[dict])
def lot_plan(lot_id: str):
    return Envelope(data=farmer_service.plan(lot_id))
