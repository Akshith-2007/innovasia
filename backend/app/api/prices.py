from datetime import date
from typing import Literal

from fastapi import APIRouter, Query

from app.schemas.common import Envelope, PriceRecord
from app.services import market_service

router = APIRouter(prefix="/market", tags=["prices"])


@router.get("/prices", response_model=Envelope[list[PriceRecord]])
def prices(
    state: str,
    district: str | None = None,
    market: str | None = None,
    commodity: str | None = None,
    live: bool = Query(True, description="Try data.gov.in first; otherwise serve stored official data (labelled cached)."),
):
    data, source, meta = market_service.latest_prices(state, district, market, commodity, prefer_live=live)
    return Envelope(data=data, source=source, meta=meta)


@router.get("/history", response_model=Envelope[list[PriceRecord]])
def history(
    state: str,
    market: str,
    commodity: str,
    district: str | None = None,
    variety: str | None = None,
    grade: str | None = None,
    start: date | None = None,
    end: date | None = None,
):
    data, source = market_service.history(state, market, commodity, district, variety, grade, start, end)
    return Envelope(data=data, source=source, meta={"count": len(data)})


@router.get("/trends", response_model=Envelope[list[dict]])
def trends(
    state: str,
    commodity: str,
    market: str | None = None,
    district: str | None = None,
    freq: Literal["W", "M"] = "M",
    start: date | None = None,
    end: date | None = None,
):
    data, source = market_service.trends(state, commodity, market, district, freq, start, end)
    return Envelope(data=data, source=source, meta={"freq": freq, "note": "Periods without observations are omitted."})


@router.get("/compare", response_model=Envelope[list[PriceRecord]])
def compare(state: str, commodity: str, district: str | None = None, on_or_before: date | None = None):
    data, source = market_service.compare(state, commodity, on_or_before, district)
    return Envelope(
        data=data, source=source, meta={"note": "Latest observation per market; each row has its own date."}
    )
