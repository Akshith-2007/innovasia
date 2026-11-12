"""AGMARKNET mandi-price resources on data.gov.in: field mapping and record normalisation.

Prices are published in INR per quintal. We keep that unit and record it explicitly.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from app.core.config import Settings, get_settings
from app.providers.data_gov import DataGovClient, ResourcePage

PRICE_UNIT = "INR/quintal"
PUBLISHER = "Directorate of Marketing and Inspection (DMI), Ministry of Agriculture and Farmers Welfare / AGMARKNET"

CANONICAL_FIELDS = (
    "state",
    "district",
    "market",
    "commodity",
    "variety",
    "grade",
    "arrival_date",
    "min_price",
    "max_price",
    "modal_price",
)

# Raw field names seen across AGMARKNET resources, after `normalise_key`.
_ALIASES: dict[str, str] = {
    "state": "state",
    "district": "district",
    "market": "market",
    "commodity": "commodity",
    "variety": "variety",
    "grade": "grade",
    "arrival_date": "arrival_date",
    "min_price": "min_price",
    "max_price": "max_price",
    "modal_price": "modal_price",
    "commodity_code": "commodity_code",
    # Column headers seen in CSV exports from data.gov.in catalogue pages and AGMARKNET reports.
    "state_name": "state",
    "district_name": "district",
    "market_name": "market",
    "commodity_name": "commodity",
    "price_date": "arrival_date",
    "reported_date": "arrival_date",
    "date": "arrival_date",
    "min_price_rs_quintal": "min_price",
    "max_price_rs_quintal": "max_price",
    "modal_price_rs_quintal": "modal_price",
}


def unsupported_unit_headers(headers: list[str]) -> list[str]:
    """Price columns not in Rs./quintal (e.g. Rs./kg). We refuse rather than guess a conversion."""
    return [h for h in headers if "price" in normalise_key(h) and "kg" in normalise_key(h)]


def normalise_key(key: str) -> str:
    k = key.replace("_x0020_", "_").strip().lower()
    k = re.sub(r"[^a-z0-9]+", "_", k).strip("_")
    return k


def parse_arrival_date(value: Any) -> date | None:
    if value is None:
        return None
    text = str(value).strip()
    for fmt in (
        "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ",
        "%d %b %Y", "%d-%b-%Y", "%d-%b-%y", "%d %B %Y",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_price(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text == "" or text.upper() in {"NA", "N/A", "NR", "-"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


def normalise_record(raw: dict[str, Any]) -> dict[str, Any]:
    """Map one raw record to canonical columns. Unparseable values become None, never guesses."""
    mapped: dict[str, Any] = {}
    for key, value in raw.items():
        canon = _ALIASES.get(normalise_key(key))
        if canon:
            mapped[canon] = value
    return {
        "state": _clean_text(mapped.get("state")),
        "district": _clean_text(mapped.get("district")),
        "market": _clean_text(mapped.get("market")),
        "commodity": _clean_text(mapped.get("commodity")),
        "variety": _clean_text(mapped.get("variety")),
        "grade": _clean_text(mapped.get("grade")),
        "arrival_date": parse_arrival_date(mapped.get("arrival_date")),
        "arrival_date_raw": None if mapped.get("arrival_date") is None else str(mapped.get("arrival_date")),
        "min_price": parse_price(mapped.get("min_price")),
        "max_price": parse_price(mapped.get("max_price")),
        "modal_price": parse_price(mapped.get("modal_price")),
        "price_unit": PRICE_UNIT,
    }


def schema_signature(page: ResourcePage) -> list[str]:
    if page.fields:
        return sorted(str(f.get("id") or f.get("name")) for f in page.fields)
    return sorted(page.records[0].keys()) if page.records else []


def missing_canonical_fields(page: ResourcePage) -> list[str]:
    present = {_ALIASES.get(normalise_key(k)) for k in schema_signature(page)}
    return [f for f in CANONICAL_FIELDS if f not in present]


def resource_url(resource_id: str) -> str:
    return f"https://api.data.gov.in/resource/{resource_id}"


def fetch_current_prices(
    filters: dict[str, str],
    client: DataGovClient | None = None,
    settings: Settings | None = None,
    max_records: int = 5000,
) -> tuple[list[dict[str, Any]], ResourcePage | None]:
    """Fetch today's published prices. Filter keys are canonical names (state, district, market, commodity).

    data.gov.in resources differ in whether filters need a `.keyword` suffix; we try the plain
    field id first and, if nothing matches, retry with the suffix. Results are re-checked locally.
    """
    settings = settings or get_settings()
    own_client = client is None
    client = client or DataGovClient(settings)
    try:
        resource_id = settings.agmarknet_current_resource_id
        records: list[dict[str, Any]] = []
        first: ResourcePage | None = None
        for suffix in ("", ".keyword"):
            keyed = {f"{k}{suffix}": v for k, v in filters.items()}
            records, first = [], None
            for page in client.iter_pages(resource_id, filters=keyed, max_records=max_records):
                first = first or page
                records.extend(page.records)
            if records or not filters:
                break
        normalised = [normalise_record(r) for r in records]
        wanted = {k: v.casefold() for k, v in filters.items()}
        normalised = [
            r for r in normalised if all((r.get(k) or "").casefold() == v for k, v in wanted.items())
        ]
        return normalised, first
    finally:
        if own_client:
            client.close()
