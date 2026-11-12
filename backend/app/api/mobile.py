"""Raithanna Android app endpoints (ADR-030). Read-only over admin-created lots; no farmer can create lots."""

from typing import Literal

from fastapi import APIRouter, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.schemas.common import Envelope
from app.services import mobile_service

router = APIRouter(prefix="/mobile", tags=["raithanna mobile"])


class IdentifyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=10, max_length=20, pattern=r"^\+?[0-9 -]+$")


class AdvisoryRequest(BaseModel):
    stage: Literal["greeting", "report", "goodbye"]
    language: Literal["te", "en"] = "te"
    audio: bool = True


@router.post("/identify", response_model=Envelope[list[dict]])
def identify(req: IdentifyRequest):
    """Demo identification (not OTP): name and number must both match an admin-created lot."""
    return Envelope(data=mobile_service.identify(req.name, req.phone),
                    meta={"verification": "none (demo identification, number not verified)"})


@router.get("/lots/{lot_id}", response_model=Envelope[dict])
def lot(lot_id: str, x_farmer_token: str | None = Header(None)):
    return Envelope(data=mobile_service.lot_view(mobile_service.authorize(lot_id, x_farmer_token)))


@router.get("/lots/{lot_id}/market", response_model=Envelope[dict])
def market(lot_id: str, mandi: str, x_farmer_token: str | None = Header(None)):
    return Envelope(data=mobile_service.live_market(mobile_service.authorize(lot_id, x_farmer_token), mandi))


@router.post("/lots/{lot_id}/advisory", response_model=Envelope[dict])
def advisory(lot_id: str, req: AdvisoryRequest, x_farmer_token: str | None = Header(None)):
    lot = mobile_service.authorize(lot_id, x_farmer_token)
    return Envelope(data=mobile_service.advisory(lot, req.stage, req.language, req.audio))


@router.get("/lots/{lot_id}/audio/{key}")
def audio(lot_id: str, key: str, x_farmer_token: str | None = Header(None)):
    mobile_service.authorize(lot_id, x_farmer_token)
    return FileResponse(mobile_service.audio_file(key), media_type="audio/mpeg",
                        headers={"Cache-Control": "private, max-age=86400"})
