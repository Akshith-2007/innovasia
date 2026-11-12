from fastapi import APIRouter

from app.schemas.common import Envelope
from app.services import statistics_service as stats

router = APIRouter(prefix="/agriculture", tags=["agricultural statistics"])


@router.get("/options", response_model=Envelope[dict])
def options():
    return Envelope(data=stats.options(), source=stats.source())


@router.get("/production", response_model=Envelope[list[dict]])
def production(state: str, crop: str, district: str | None = None, season: str | None = None):
    data, source = stats.production(state, crop, district, season)
    return Envelope(data=data, source=source)


@router.get("/yield", response_model=Envelope[list[dict]])
def yield_(state: str, crop: str, district: str | None = None):
    data, source = stats.yield_series(state, crop, district)
    return Envelope(data=data, source=source, meta={"note": stats.YIELD_NOTE})


@router.get("/district-comparison", response_model=Envelope[list[dict]])
def district_comparison(state: str, crop: str, year: int | None = None):
    data, source, used_year = stats.district_comparison(state, crop, year)
    return Envelope(data=data, source=source, meta={"year": used_year, "note": stats.YIELD_NOTE})
