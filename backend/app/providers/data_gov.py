"""Generic client for the Open Government Data (OGD) Platform India resource API.

This is the only module that talks to api.data.gov.in. It never invents data: every failure
raises UpstreamError with a `kind` the API layer can report to the user.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import NotConfiguredError, UpstreamError

log = logging.getLogger(__name__)

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


@dataclass
class ResourcePage:
    resource_id: str
    offset: int
    limit: int
    total: int | None
    records: list[dict[str, Any]]
    fields: list[dict[str, Any]]
    title: str | None
    org: list[str]
    updated_date: str | None
    retrieved_at: str
    raw: dict[str, Any] = field(repr=False)
    raw_bytes: bytes = field(default=b"", repr=False)
    request_params: dict[str, Any] = field(default_factory=dict)


class DataGovClient:
    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.BaseTransport | None = None,
        max_retries: int = 3,
        backoff_seconds: float = 2.0,
    ) -> None:
        self.settings = settings or get_settings()
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self._client = httpx.Client(
            base_url=self.settings.data_gov_base_url,
            timeout=self.settings.http_timeout_seconds,
            transport=transport,
            headers={"Accept": "application/json", "User-Agent": "kisan-cold-link-backend/0.1"},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> DataGovClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def fetch_page(
        self,
        resource_id: str,
        offset: int = 0,
        limit: int | None = None,
        filters: dict[str, str] | None = None,
    ) -> ResourcePage:
        if not self.settings.has_api_key:
            raise NotConfiguredError(
                "DATA_GOV_API_KEY is not set. Add your personal data.gov.in key to backend/.env."
            )
        limit = limit or self.settings.page_size
        params: dict[str, str | int] = {
            "api-key": self.settings.data_gov_api_key,
            "format": "json",
            "offset": offset,
            "limit": limit,
        }
        for key, value in (filters or {}).items():
            params[f"filters[{key}]"] = value

        payload, content = self._get_json(f"/{resource_id}", params)
        page = self._parse_page(resource_id, offset, limit, payload)
        page.raw_bytes = content
        page.request_params = {k: v for k, v in params.items() if k != "api-key"}
        return page

    def iter_pages(
        self,
        resource_id: str,
        filters: dict[str, str] | None = None,
        limit: int | None = None,
        max_records: int | None = None,
        pause_seconds: float = 0.5,
    ) -> Iterator[ResourcePage]:
        """Walk offset pagination until the reported total is reached or a short page arrives."""
        offset = 0
        seen = 0
        while True:
            page = self.fetch_page(resource_id, offset=offset, limit=limit, filters=filters)
            yield page
            n = len(page.records)
            seen += n
            offset += n
            if n == 0 or n < page.limit:
                return
            if page.total is not None and offset >= page.total:
                return
            if max_records is not None and seen >= max_records:
                return
            if pause_seconds:
                time.sleep(pause_seconds)

    # -- internals -----------------------------------------------------------------------

    def _get_json(self, path: str, params: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
        attempt = 0
        while True:
            attempt += 1
            try:
                resp = self._client.get(path, params=params)
            except httpx.TimeoutException as exc:
                if attempt <= self.max_retries:
                    self._sleep(attempt)
                    continue
                raise UpstreamError("data.gov.in request timed out", kind="timeout") from exc
            except httpx.HTTPError as exc:
                raise UpstreamError(f"Could not reach data.gov.in: {exc}", kind="network") from exc

            if resp.status_code in (401, 403):
                raise UpstreamError(
                    "data.gov.in rejected the API key", kind="auth", details={"status": resp.status_code}
                )
            if resp.status_code in RETRYABLE_STATUS:
                if attempt <= self.max_retries:
                    self._sleep(attempt, resp.headers.get("Retry-After"))
                    continue
                kind = "rate_limited" if resp.status_code == 429 else "server_error"
                raise UpstreamError(
                    f"data.gov.in returned HTTP {resp.status_code}", kind=kind, details={"status": resp.status_code}
                )
            if resp.status_code >= 400:
                raise UpstreamError(
                    f"data.gov.in returned HTTP {resp.status_code}", kind="http_error", details={"status": resp.status_code}
                )
            try:
                payload = resp.json()
            except ValueError as exc:
                raise UpstreamError("data.gov.in returned a non-JSON response", kind="invalid_response") from exc
            if not isinstance(payload, dict):
                raise UpstreamError("data.gov.in returned an unexpected payload", kind="invalid_response")
            status = str(payload.get("status", "ok")).lower()
            if status not in ("ok", "success"):
                message = str(payload.get("message") or "unknown error")
                kind = "auth" if "key" in message.lower() else "invalid_response"
                raise UpstreamError(f"data.gov.in error: {message}", kind=kind)
            return payload, resp.content

    def _sleep(self, attempt: int, retry_after: str | None = None) -> None:
        delay = self.backoff_seconds * (2 ** (attempt - 1))
        if retry_after and retry_after.isdigit():
            delay = max(delay, float(retry_after))
        log.warning("data.gov.in retry %s in %.1fs", attempt, delay)
        time.sleep(delay)

    @staticmethod
    def _parse_page(resource_id: str, offset: int, limit: int, payload: dict[str, Any]) -> ResourcePage:
        records = payload.get("records")
        if not isinstance(records, list):
            raise UpstreamError(
                "data.gov.in response has no 'records' list (possible schema change)", kind="schema_change"
            )
        total_raw = payload.get("total")
        try:
            total = int(total_raw) if total_raw is not None else None
        except (TypeError, ValueError):
            total = None
        org = payload.get("org") or []
        return ResourcePage(
            resource_id=resource_id,
            offset=offset,
            limit=limit,
            total=total,
            records=[r for r in records if isinstance(r, dict)],
            fields=[f for f in payload.get("field") or [] if isinstance(f, dict)],
            title=payload.get("title"),
            org=[str(o) for o in org] if isinstance(org, list) else [str(org)],
            updated_date=payload.get("updated_date"),
            retrieved_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            raw=payload,
        )
