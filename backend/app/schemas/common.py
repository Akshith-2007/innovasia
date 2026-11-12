from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class SourceInfo(BaseModel):
    dataset: str
    name: str
    publisher: list[str] | str | None = None
    resource_id: str | None = None
    resource_url: str | None = None
    retrieved_at: str | None = None
    observation_range: list[str] | None = None
    live: bool = Field(description="True only when values came from data.gov.in during this request window")
    cached: bool = Field(description="True when served from locally stored downloads")
    third_party: bool = Field(False, description="True when any rows come from a third-party mirror (ADR-022)")
    licence: str | None = None
    note: str | None = None


class Envelope(BaseModel, Generic[T]):
    data: T
    source: SourceInfo | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class PriceRecord(BaseModel):
    state: str
    district: str | None
    market: str
    commodity: str
    variety: str | None
    grade: str | None
    arrival_date: str
    min_price: float | None
    max_price: float | None
    modal_price: float
    price_unit: str = "INR/quintal"
    source_kind: str | None = None  # "official" | "third_party_mirror"; None for live API rows


class PredictRequest(BaseModel):
    state: str
    district: str | None = None
    market: str
    commodity: str
    variety: str | None = None
    grade: str | None = None


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
