from fastapi import APIRouter, Query

from app.schemas.common import Envelope
from app.services import market_service

router = APIRouter(prefix="/markets", tags=["market discovery"])


@router.get("/states", response_model=Envelope[list[str]])
def list_states():
    return Envelope(data=market_service.states(), source=market_service.local_source())


@router.get("/districts", response_model=Envelope[list[str]])
def list_districts(state: str = Query(...)):
    return Envelope(data=market_service.districts(state), source=market_service.local_source())


@router.get("/list", response_model=Envelope[list[dict]])
def list_markets(state: str | None = None, district: str | None = None, commodity: str | None = None):
    return Envelope(data=market_service.markets(state, district, commodity), source=market_service.local_source())
