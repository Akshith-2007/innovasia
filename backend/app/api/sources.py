from fastapi import APIRouter

from app.services import data_service

router = APIRouter(prefix="/data", tags=["data provenance"])


@router.get("/sources")
def sources() -> dict:
    """Provenance of every processed dataset (from metadata/sources.json) and the latest quality report."""
    doc = data_service.read_metadata_file("sources.json") or {"sources": []}
    quality = data_service.read_metadata_file("quality_report.json")
    if quality and "market_prices" in quality:
        quality = {**quality, "market_prices": {k: v for k, v in quality["market_prices"].items()
                                                if k not in ("runs", "series_coverage_top")}}
    return {"generated_at": doc.get("generated_at"), "sources": doc.get("sources", []), "quality": quality}
