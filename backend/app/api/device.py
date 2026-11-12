"""ESP32 device endpoints (device key) and cold-storage admin endpoints (admin password). ADR-024."""

import secrets
from typing import Literal

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.exceptions import AppError, NotConfiguredError
from app.schemas.common import Envelope
from app.services import device_service

router = APIRouter(tags=["cold storage device"])
MAX_POINTS = 1500


class Unauthorized(AppError):
    status_code = 401
    code = "unauthorized"


def _check(given: str | None, expected: str, what: str) -> None:
    if not expected:
        raise NotConfiguredError(f"{what} is not configured in backend/.env.")
    if not given or not secrets.compare_digest(given.encode(), expected.encode()):
        raise Unauthorized(f"Wrong or missing {what.lower()}.")


def require_device(x_device_key: str | None = Header(None)) -> None:
    _check(x_device_key, get_settings().device_key, "DEVICE_KEY")


def require_admin(x_admin_password: str | None = Header(None)) -> None:
    _check(x_admin_password, get_settings().admin_password, "ADMIN_PASSWORD")


class Telemetry(BaseModel):
    chamber_temp_c: float | None = Field(None, ge=-40, le=80, description="DHT11 chamber air temperature")
    humidity_pct: float | None = Field(None, ge=0, le=100, description="DHT11 relative humidity")
    coil_temp_c: float | None = Field(None, ge=-55, le=125, description="DS18B20 coil / heat-sink water temperature")
    pump_on: bool = Field(description="Pump state the device actually has")
    uptime_s: int | None = Field(None, ge=0)


class AutoLimits(BaseModel):
    upper_c: float | None = Field(None, ge=-20, le=40)
    lower_c: float | None = Field(None, ge=-20, le=40)


class PcmSettings(BaseModel):
    mass_kg: float | None = Field(None, gt=0, le=10_000, description="PCM mass")
    latent_kj_per_kg: float | None = Field(None, gt=0, le=1_000, description="Latent heat of fusion (water/ice: 334)")
    melt_c: float | None = Field(None, ge=-40, le=40, description="PCM melting point")
    ambient_c: float | None = Field(None, ge=-10, le=55, description="Outside air temperature around the chamber")
    wall_area_m2: float | None = Field(None, gt=0, le=1_000, description="Total insulated surface area")
    insulation_mm: float | None = Field(None, gt=0, le=1_000, description="Insulation thickness")
    insulation_k: float | None = Field(None, gt=0, le=1, description="Insulation conductivity, W/m·K")
    coil_w_per_k: float | None = Field(None, ge=0, le=10_000, description="Coil-to-PCM heat transfer, W/K (optional)")


class Control(BaseModel):
    mode: Literal["manual", "auto"] | None = None
    pump_on: bool | None = None
    auto: AutoLimits | None = None
    pcm: PcmSettings | None = None
    pcm_reset_full: bool = False


@router.post("/device/telemetry", dependencies=[Depends(require_device)])
def post_telemetry(reading: Telemetry) -> dict:
    """ESP32 sends readings; the reply carries the pump state it should apply."""
    return device_service.record_telemetry(reading.model_dump())


@router.get("/device/command", dependencies=[Depends(require_device)])
def get_command() -> dict:
    return device_service.command()


@router.get("/admin/device", response_model=Envelope[dict], dependencies=[Depends(require_admin)])
def admin_status():
    return Envelope(data=device_service.status())


@router.get("/admin/telemetry", response_model=Envelope[list[dict]], dependencies=[Depends(require_admin)])
def admin_telemetry(hours: float = Query(6, gt=0, le=24 * 7)):
    rows = device_service.telemetry(hours)
    step = max(1, len(rows) // MAX_POINTS)
    return Envelope(data=rows[::step], meta={"points": len(rows), "every_nth": step})


@router.put("/admin/device/control", response_model=Envelope[dict], dependencies=[Depends(require_admin)])
def admin_control(change: Control):
    payload = change.model_dump(exclude_none=True)
    device_service.update_control(payload)
    return Envelope(data=device_service.status())
