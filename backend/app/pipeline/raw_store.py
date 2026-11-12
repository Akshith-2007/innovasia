"""Immutable raw-data store.

Each fetch/import is a *run* in its own directory:

    data/raw/<dataset>/<run_id>/
        page_0001.json ...      exact bytes returned by data.gov.in (or the original imported file)
        manifest.json           provenance: source, resource id, filters, checksums, counts

Files are created with exclusive mode and marked read-only. Nothing here ever overwrites.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import Settings, get_settings
from app.providers.data_gov import ResourcePage

MANIFEST = "manifest.json"
SCHEMA_VERSION = "1"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_once(path: Path, data: bytes) -> None:
    with path.open("xb") as fh:  # raises FileExistsError rather than overwrite
        fh.write(data)
    os.chmod(path, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)


def new_run_dir(dataset: str, label: str, settings: Settings | None = None) -> tuple[str, Path]:
    settings = settings or get_settings()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe = "".join(c if c.isalnum() else "-" for c in label.lower()).strip("-")[:60] or "all"
    run_id = f"{stamp}_{safe}"
    run_dir = settings.raw_dir / dataset / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_id, run_dir


@dataclass
class RunSummary:
    run_id: str
    run_dir: Path
    record_count: int
    pages: int


def store_api_pages(
    dataset: str,
    label: str,
    source_name: str,
    resource_id: str,
    resource_url: str,
    filters: dict[str, str],
    pages: Iterable[ResourcePage],
    extra: dict[str, Any] | None = None,
    settings: Settings | None = None,
) -> RunSummary:
    run_id, run_dir = new_run_dir(dataset, label, settings)
    page_entries: list[dict[str, Any]] = []
    total_reported: int | None = None
    title: str | None = None
    org: list[str] = []
    updated_date: str | None = None
    fields: list[dict[str, Any]] = []
    first_retrieved: str | None = None
    last_retrieved: str | None = None
    for i, page in enumerate(pages, start=1):
        name = f"page_{i:04d}.json"
        _write_once(run_dir / name, page.raw_bytes)
        page_entries.append(
            {
                "file": name,
                "sha256": sha256_bytes(page.raw_bytes),
                "offset": page.offset,
                "total": page.total,
                "records": len(page.records),
                "retrieved_at": page.retrieved_at,
                "request_params": page.request_params,
            }
        )
        total_reported = page.total if page.total is not None else total_reported
        title = title or page.title
        org = org or page.org
        updated_date = updated_date or page.updated_date
        fields = fields or page.fields
        first_retrieved = first_retrieved or page.retrieved_at
        last_retrieved = page.retrieved_at

    record_count = sum(p["records"] for p in page_entries)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "dataset": dataset,
        "run_id": run_id,
        "kind": "api",
        "source_name": source_name,
        "title": title,
        "publisher": org,
        "resource_id": resource_id,
        "resource_url": resource_url,
        "catalogue_updated_date": updated_date,
        "retrieved_at_start": first_retrieved,
        "retrieved_at_end": last_retrieved,
        "filters": filters,
        "total_reported_by_api": total_reported,
        "record_count": record_count,
        "complete": _complete(page_entries, record_count),
        "fields": fields,
        "pages": page_entries,
        **(extra or {}),
    }
    _write_once(run_dir / MANIFEST, json.dumps(manifest, indent=2, default=str).encode())
    return RunSummary(run_id, run_dir, record_count, len(page_entries))


def _complete(pages: list[dict[str, Any]], record_count: int) -> bool | None:
    """A run may hold several queries (e.g. one per day); expected = sum of each query's reported total."""
    totals: dict[str, int] = {}
    for p in pages:
        if p.get("total") is None:
            return None
        q = json.dumps({k: v for k, v in p["request_params"].items() if k not in ("offset", "limit")}, sort_keys=True)
        totals[q] = max(totals.get(q, 0), int(p["total"]))
    return record_count >= sum(totals.values())


def import_file(
    dataset: str,
    source_file: Path,
    source_name: str,
    resource_id: str,
    resource_url: str,
    publisher: list[str],
    settings: Settings | None = None,
    extra: dict[str, Any] | None = None,
) -> RunSummary:
    """Preserve an officially downloaded file (e.g. CSV from a data.gov.in catalogue page)."""
    run_id, run_dir = new_run_dir(dataset, source_file.stem, settings)
    target = run_dir / source_file.name
    shutil.copyfile(source_file, target)
    os.chmod(target, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "dataset": dataset,
        "run_id": run_id,
        "kind": "file_import",
        "source_name": source_name,
        "publisher": publisher,
        "resource_id": resource_id,
        "resource_url": resource_url,
        "original_filename": source_file.name,
        "retrieved_at_start": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sha256": sha256_file(target),
        "files": [{"file": source_file.name, "sha256": sha256_file(target)}],
        **(extra or {}),
    }
    _write_once(run_dir / MANIFEST, json.dumps(manifest, indent=2).encode())
    return RunSummary(run_id, run_dir, int((extra or {}).get("record_count", -1)), 1)


def list_runs(dataset: str, settings: Settings | None = None) -> list[tuple[Path, dict[str, Any]]]:
    settings = settings or get_settings()
    root = settings.raw_dir / dataset
    if not root.exists():
        return []
    runs = []
    for manifest_path in sorted(root.glob(f"*/{MANIFEST}")):
        runs.append((manifest_path.parent, json.loads(manifest_path.read_text(encoding="utf-8"))))
    return runs


def verify_run(run_dir: Path, manifest: dict[str, Any]) -> list[str]:
    """Return checksum mismatches; an empty list means raw files are intact."""
    problems = []
    entries = manifest.get("pages") or manifest.get("files") or []
    for entry in entries:
        path = run_dir / entry["file"]
        if not path.exists():
            problems.append(f"missing {path.name}")
        elif sha256_file(path) != entry["sha256"]:
            problems.append(f"checksum mismatch {path.name}")
    return problems


def read_csv_records(path: Path) -> list[dict[str, Any]]:
    import csv
    import io

    text = path.read_bytes().decode("utf-8-sig", errors="replace")
    return [dict(r) for r in csv.DictReader(io.StringIO(text))]


def iter_run_records(run_dir: Path, manifest: dict[str, Any]) -> Iterable[dict[str, Any]]:
    if manifest.get("kind") == "file_import":
        for entry in manifest.get("files", []):
            yield from read_csv_records(run_dir / entry["file"])
        return
    for entry in manifest.get("pages", []):
        payload = json.loads((run_dir / entry["file"]).read_bytes())
        for rec in payload.get("records") or []:
            if isinstance(rec, dict):
                yield rec
