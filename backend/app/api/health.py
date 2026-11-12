from fastapi import APIRouter

from app.core.config import get_settings
from app.ml.metadata import current_version

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "api_key_configured": s.has_api_key,
        "data": {
            "market_prices": s.market_prices_path.exists(),
            "crop_production": s.crop_production_path.exists(),
        },
        "model": {"available": current_version(s.models_dir) is not None, "version": current_version(s.models_dir)},
    }
