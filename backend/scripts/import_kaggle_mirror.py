"""Import the Kaggle mirror of AGMARKNET daily prices into the raw store (ADR-022). Explicit only.

Dataset: https://www.kaggle.com/datasets/khandelwalmanas/daily-commodity-prices-india
Upstream: data.gov.in AGMARKNET "Variety-wise Daily Market Prices Data of Commodity".
Licence (as stated by the dataset): Government Open Data License - India (GODL).

Each year's Parquet file is preserved unmodified as its own read-only raw run labelled
`source_kind = "third_party_mirror"`. Official imports always win over mirror rows on conflicts.

    python -m scripts.import_kaggle_mirror --years 2022-2026            # download (no login needed)
    python -m scripts.import_kaggle_mirror --years 2024 --from-dir DIR  # use files already downloaded
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

import httpx
import pyarrow.parquet as pq

from app.pipeline import raw_store
from app.providers.agmarknet import _ALIASES, normalise_key

DATASET_SLUG = "khandelwalmanas/daily-commodity-prices-india"
DATASET_URL = f"https://www.kaggle.com/datasets/{DATASET_SLUG}"
DOWNLOAD_URL = f"https://www.kaggle.com/api/v1/datasets/download/{DATASET_SLUG}"
UPSTREAM_URL = "https://www.data.gov.in/resource/variety-wise-daily-market-prices-data-commodity"
LICENCE = "Government Open Data License - India (GODL), https://www.data.gov.in/Godl"
REQUIRED = ("state", "market", "commodity", "arrival_date", "modal_price")


def parse_years(spec: str) -> list[int]:
    years: set[int] = set()
    for part in spec.split(","):
        if "-" in part:
            a, b = (int(x) for x in part.split("-"))
            years.update(range(a, b + 1))
        else:
            years.add(int(part))
    return sorted(years)


def download(year: int, dest: Path) -> Path:
    target = dest / f"{year}.parquet"
    with httpx.stream(
        "GET", DOWNLOAD_URL, params={"fileName": f"parquet/{year}.parquet"},
        follow_redirects=True, timeout=600, headers={"User-Agent": "kisan-cold-link-importer/0.1"},
    ) as r:
        if r.status_code != 200:
            raise SystemExit(f"{year}: Kaggle returned HTTP {r.status_code}")
        with target.open("wb") as fh:
            for chunk in r.iter_bytes(1 << 20):
                fh.write(chunk)
    return target


def check_file(path: Path) -> int:
    with path.open("rb") as fh:
        if fh.read(4) != b"PAR1":
            raise SystemExit(f"{path.name} is not a Parquet file")
    meta = pq.read_metadata(path)
    names = pq.read_schema(path).names
    mapped = {_ALIASES.get(normalise_key(n)) for n in names}
    missing = [c for c in REQUIRED if c not in mapped]
    if missing:
        raise SystemExit(f"{path.name} lacks required columns {missing}; columns: {names}")
    if any("kg" in normalise_key(n) for n in names if "price" in normalise_key(n)):
        raise SystemExit(f"{path.name} has per-kg price columns; refusing to guess units")
    return meta.num_rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--years", default="2022-2026", help="e.g. 2022-2026 or 2023,2025")
    p.add_argument("--from-dir", help="directory with <year>.parquet files already downloaded from Kaggle")
    args = p.parse_args(argv)

    existing = {m.get("original_filename") for _, m in raw_store.list_runs("agmarknet")
                if m.get("source_kind") == "third_party_mirror"}
    tmp = Path(tempfile.mkdtemp(prefix="kcl-kaggle-"))
    try:
        for year in parse_years(args.years):
            name = f"{year}.parquet"
            if name in existing:
                print(f"{year}: already imported, skipping (raw runs are immutable)")
                continue
            src = Path(args.from_dir) / name if args.from_dir else download(year, tmp)
            if not src.is_file():
                raise SystemExit(f"{src} not found")
            rows = check_file(src)
            summary = raw_store.import_file(
                dataset="agmarknet",
                source_file=src,
                source_name="AGMARKNET daily prices via Kaggle mirror (khandelwalmanas/daily-commodity-prices-india)",
                resource_id=f"kaggle:{DATASET_SLUG}",
                resource_url=DATASET_URL,
                publisher=["Kaggle user khandelwalmanas (third-party mirror of data.gov.in AGMARKNET)"],
                extra={
                    "source_kind": "third_party_mirror",
                    "upstream_source": "data.gov.in AGMARKNET variety-wise daily market prices",
                    "upstream_url": UPSTREAM_URL,
                    "licence": LICENCE,
                    "download_url": f"{DOWNLOAD_URL}?fileName=parquet/{year}.parquet",
                    "record_count": rows,
                    "complete": None,
                    "fields": [{"id": n} for n in pq.read_schema(src).names],
                },
            )
            print(f"{year}: preserved {rows:,} rows -> {summary.run_dir.name}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("next: python -m scripts.preprocess_data   (scope: MARKET_STATES in backend/.env)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
