"""Fetch official data from data.gov.in into the immutable raw store. Run explicitly; never automatic.

Examples (from backend/):
    python -m scripts.fetch_official_data probe --resource history
    python -m scripts.fetch_official_data current --state Telangana
    python -m scripts.fetch_official_data history --state Telangana --commodity Tomato
    python -m scripts.fetch_official_data crop-api
    python -m scripts.fetch_official_data crop-import path/to/downloaded.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator
from datetime import date, timedelta

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.pipeline import raw_store
from app.providers import agmarknet
from app.providers.agmarknet import normalise_key
from app.providers.data_gov import DataGovClient, ResourcePage


def _resource(name: str) -> str:
    s = get_settings()
    return {
        "current": s.agmarknet_current_resource_id,
        "history": s.agmarknet_history_resource_id,
        "crop": s.crop_production_resource_id,
    }[name]


def _field_ids(client: DataGovClient, resource_id: str) -> dict[str, str]:
    """Map normalised field name -> the resource's actual field id."""
    page = client.fetch_page(resource_id, limit=1)
    ids = [str(f.get("id")) for f in page.fields if f.get("id")] or list(page.records[0].keys() if page.records else [])
    return {normalise_key(i): i for i in ids}


def _pages_with_filters(
    client: DataGovClient, resource_id: str, filters: dict[str, str], max_records: int | None
) -> Iterator[ResourcePage]:
    """Resolve filter names to the resource's field ids; try plain then `.keyword` variants."""
    if not filters:
        yield from client.iter_pages(resource_id, max_records=max_records)
        return
    ids = _field_ids(client, resource_id)
    resolved = {}
    for canon, value in filters.items():
        fid = ids.get(canon) or ids.get(f"{canon}_name")
        if not fid:
            raise SystemExit(f"Resource {resource_id} has no field for filter '{canon}'. Fields: {sorted(ids.values())}")
        resolved[fid] = value
    for suffix in ("", ".keyword"):
        keyed = {f"{k}{suffix}": v for k, v in resolved.items()}
        first = client.fetch_page(resource_id, limit=1, filters=keyed)
        if first.records:
            print(f"filters matched with keys {list(keyed)}; total reported: {first.total}")
            yield from client.iter_pages(resource_id, filters=keyed, max_records=max_records)
            return
    raise SystemExit(f"No records matched filters {filters} (tried plain and .keyword field names).")


def cmd_probe(args: argparse.Namespace) -> None:
    rid = _resource(args.resource)
    with DataGovClient() as client:
        page = client.fetch_page(rid, limit=args.limit)
    dates = sorted(
        {str(agmarknet.parse_arrival_date(r.get(k))) for r in page.records for k in r if "date" in k.lower()}
    )
    print(json.dumps(
        {
            "resource_id": rid,
            "title": page.title,
            "publisher": page.org,
            "catalogue_updated_date": page.updated_date,
            "total_reported": page.total,
            "fields": [{"id": f.get("id"), "name": f.get("name"), "type": f.get("type")} for f in page.fields],
            "sample_dates_in_page": dates[:10],
            "records_in_page": len(page.records),
        },
        indent=2,
    ))


def _day_range(args: argparse.Namespace) -> list[date]:
    if not args.from_date:
        return []
    start = date.fromisoformat(args.from_date)
    end = date.fromisoformat(args.to_date) if args.to_date else date.today()
    if end < start:
        raise SystemExit("--to is before --from")
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def _pages_by_day(client: DataGovClient, resource_id: str, filters: dict[str, str], days: list[date]) -> Iterator[ResourcePage]:
    """One filtered query per arrival date (the API filters dates by exact dd/mm/yyyy match)."""
    ids = _field_ids(client, resource_id)
    keyed = {ids.get(k, k): v for k, v in filters.items()}
    date_key = ids.get("arrival_date")
    if not date_key:
        raise SystemExit(f"Resource {resource_id} has no arrival date field")
    for i, d in enumerate(days, 1):
        n = 0
        for page in client.iter_pages(resource_id, filters={**keyed, date_key: d.strftime("%d/%m/%Y")}):
            n += len(page.records)
            yield page
        print(f"  {d}  {n} records  ({i}/{len(days)})", flush=True)


def cmd_market(args: argparse.Namespace, which: str) -> None:
    rid = _resource(which)
    filters = {k: v for k, v in {"state": args.state, "district": args.district, "market": args.market,
                                 "commodity": args.commodity}.items() if v}
    days = _day_range(args) if which == "history" else []
    label = "-".join([which, *filters.values(), *([f"{days[0]}_{days[-1]}"] if days else [])])
    if days:
        filters["arrival_date_range"] = f"{days[0]}..{days[-1]}"
    with DataGovClient() as client:
        pages = (
            _pages_by_day(client, rid, {k: v for k, v in filters.items() if k != "arrival_date_range"}, days)
            if days
            else _pages_with_filters(client, rid, filters, args.max_records)
        )
        summary = raw_store.store_api_pages(
            dataset="agmarknet",
            label=label,
            source_name=f"AGMARKNET {which} mandi prices",
            resource_id=rid,
            resource_url=agmarknet.resource_url(rid),
            filters=filters,
            pages=pages,
            extra={"resource_role": which},
        )
    print(f"stored {summary.record_count} records in {summary.pages} pages -> {summary.run_dir}")


def cmd_crop_api(args: argparse.Namespace) -> None:
    rid = _resource("crop")
    filters = {k: v for k, v in {"state": args.state}.items() if v}
    with DataGovClient() as client:
        summary = raw_store.store_api_pages(
            dataset="crop_production",
            label="crop-" + (args.state or "all"),
            source_name="District-wise season-wise crop production statistics",
            resource_id=rid,
            resource_url=agmarknet.resource_url(rid),
            filters=filters,
            pages=_pages_with_filters(client, rid, filters, args.max_records),
        )
    print(f"stored {summary.record_count} records -> {summary.run_dir}")


def cmd_crop_import(args: argparse.Namespace) -> None:
    from pathlib import Path

    src = Path(args.file)
    if not src.is_file():
        raise SystemExit(f"{src} not found")
    summary = raw_store.import_file(
        dataset="crop_production",
        source_file=src,
        source_name="District-wise season-wise crop production statistics",
        resource_id=args.resource_id or _resource("crop"),
        resource_url=args.url,
        publisher=[args.publisher],
    )
    print(f"preserved {src.name} -> {summary.run_dir}")


def cmd_market_import(args: argparse.Namespace) -> None:
    """Preserve an officially downloaded AGMARKNET price CSV (no API key needed)."""
    from pathlib import Path

    src = Path(args.file)
    if not src.is_file():
        raise SystemExit(f"{src} not found")
    if src.suffix.lower() != ".csv":
        raise SystemExit("Only .csv exports are supported. Save the official download as CSV (not Excel).")
    rows = raw_store.read_csv_records(src)
    if not rows:
        raise SystemExit(f"{src.name} has no data rows.")
    headers = list(rows[0].keys())
    bad_units = agmarknet.unsupported_unit_headers(headers)
    if bad_units:
        raise SystemExit(f"Price columns not in Rs./quintal: {bad_units}. Refusing to guess a unit conversion.")
    mapped = {agmarknet._ALIASES.get(normalise_key(h)) for h in headers}
    required = ("state", "market", "commodity", "arrival_date", "modal_price")
    missing = [f for f in required if f not in mapped]
    if missing:
        raise SystemExit(f"{src.name} is missing required columns {missing}. Headers found: {headers}")
    summary = raw_store.import_file(
        dataset="agmarknet",
        source_file=src,
        source_name=args.source_name,
        resource_id=args.resource_id,
        resource_url=args.url,
        publisher=[args.publisher],
        extra={
            "record_count": len(rows),
            "complete": None,
            "fields": [{"id": h} for h in headers],
            "resource_role": "history",
        },
    )
    print(f"preserved {src.name} ({len(rows)} rows) -> {summary.run_dir}")
    print("next: python -m scripts.validate_data && python -m scripts.preprocess_data")


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("probe", help="Inspect a resource: fields, total, sample dates")
    pr.add_argument("--resource", choices=["current", "history", "crop"], default="history")
    pr.add_argument("--limit", type=int, default=10)

    for name in ("current", "history"):
        sp = sub.add_parser(name, help=f"Fetch AGMARKNET {name} prices")
        sp.add_argument("--state")
        sp.add_argument("--district")
        sp.add_argument("--market")
        sp.add_argument("--commodity")
        sp.add_argument("--max-records", type=int, default=None)
        if name == "history":
            sp.add_argument("--from", dest="from_date", help="first arrival date, YYYY-MM-DD (one query per day)")
            sp.add_argument("--to", dest="to_date", help="last arrival date, YYYY-MM-DD (default: today)")

    ca = sub.add_parser("crop-api", help="Fetch crop production statistics via API")
    ca.add_argument("--state")
    ca.add_argument("--max-records", type=int, default=None)

    ci = sub.add_parser("crop-import", help="Preserve an officially downloaded crop production CSV")
    ci.add_argument("file")
    ci.add_argument("--resource-id")
    ci.add_argument(
        "--url", default="https://www.data.gov.in/catalog/district-wise-season-wise-crop-production-statistics-0"
    )
    ci.add_argument("--publisher", default="Ministry of Agriculture and Farmers Welfare")

    mi = sub.add_parser("market-import", help="Preserve an officially downloaded mandi-price CSV (no key needed)")
    mi.add_argument("file")
    mi.add_argument("--resource-id", default=get_settings().agmarknet_history_resource_id,
                    help="data.gov.in resource id the file was downloaded from")
    mi.add_argument("--url", required=True, help="Page the file was downloaded from (recorded as provenance)")
    mi.add_argument("--source-name", default="AGMARKNET mandi prices (official CSV download)")
    mi.add_argument("--publisher", default="Directorate of Marketing and Inspection / AGMARKNET")

    args = p.parse_args(argv)
    try:
        if args.cmd == "probe":
            cmd_probe(args)
        elif args.cmd in ("current", "history"):
            cmd_market(args, args.cmd)
        elif args.cmd == "crop-api":
            cmd_crop_api(args)
        elif args.cmd == "market-import":
            cmd_market_import(args)
        else:
            cmd_crop_import(args)
    except AppError as exc:
        print(f"ERROR [{exc.code}] {exc.message} {exc.details or ''}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
