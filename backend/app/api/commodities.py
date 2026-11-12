from fastapi import APIRouter

from app.schemas.common import Envelope
from app.services import market_service

router = APIRouter(prefix="/commodities", tags=["commodities"])


@router.get("", response_model=Envelope[list[dict]])
def list_commodities(state: str | None = None, district: str | None = None, market: str | None = None):
    return Envelope(data=market_service.commodities(state, district, market), source=market_service.local_source())


@router.get("/{commodity}/varieties", response_model=Envelope[list[dict]])
def list_varieties(commodity: str, market: str | None = None):
    return Envelope(data=market_service.varieties(commodity, market), source=market_service.local_source())
