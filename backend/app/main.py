from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import agriculture, commodities, decision, device, health, lots, markets, predictions, prices, sources
from app.core.config import get_settings
from app.core.exceptions import AppError, app_error_handler
from app.core.logging import configure_logging
from app.core.rate_limit import RateLimitMiddleware

configure_logging()

app = FastAPI(
    title="Kisan Cold Link API",
    version="0.1.0",
    description="Official AGMARKNET / data.gov.in market data, district crop statistics and a trained "
    "mandi-price forecasting model. No synthetic data.",
)
app.add_middleware(RateLimitMiddleware, per_minute=get_settings().rate_limit_per_minute)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-Admin-Password"],
)
app.add_exception_handler(AppError, app_error_handler)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Frame-Options", "DENY")
    return response

API = "/api/v1"
for r in (
    health.router, markets.router, commodities.router, prices.router,
    agriculture.router, predictions.router, sources.router, decision.router, device.router, lots.router,
):
    app.include_router(r, prefix=API)


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"service": "kisan-cold-link-api", "docs": "/docs", "health": f"{API}/health"}
