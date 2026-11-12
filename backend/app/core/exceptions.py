"""Typed errors. Every failure surfaces honestly to the client; nothing is replaced with made-up values."""

import re

from fastapi import Request
from fastapi.responses import JSONResponse

_KEY_RE = re.compile(r"(api-key=)[^&\s'\"]+", re.IGNORECASE)


def redact(text: str) -> str:
    """Strip API keys from any text that may reach logs or clients."""
    return _KEY_RE.sub(lambda m: m.group(1) + "[REDACTED]", text)


class AppError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str, details: dict | None = None) -> None:
        message = redact(message)
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotConfiguredError(AppError):
    status_code = 503
    code = "not_configured"


class DataUnavailableError(AppError):
    """Local processed data has not been generated yet."""

    status_code = 503
    code = "data_unavailable"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class InsufficientDataError(AppError):
    status_code = 422
    code = "insufficient_data"


class ModelUnavailableError(AppError):
    status_code = 503
    code = "model_unavailable"


class UpstreamError(AppError):
    """Government API failed: timeout, auth, rate limit, bad payload or schema change."""

    status_code = 502
    code = "upstream_error"

    def __init__(self, message: str, kind: str, details: dict | None = None) -> None:
        super().__init__(message, {"kind": kind, **(details or {})})
        self.kind = kind


async def app_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )


class InputRequiredError(AppError):
    """A value has no published default and the user did not supply one; never assume it."""

    status_code = 422
    code = "input_required"


class AmbiguousSeriesError(AppError):
    """The selection matches several varieties/grades; the user must pick one (never guessed)."""

    status_code = 422
    code = "ambiguous_series"
