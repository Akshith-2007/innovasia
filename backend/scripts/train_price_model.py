"""Train the mandi modal-price model on processed official data. Explicit command only.

    python -m scripts.train_price_model            # assess coverage, train, save artifact
    python -m scripts.train_price_model --assess   # only report which series are eligible
"""

from __future__ import annotations

import argparse
import json
import sys

import pandas as pd

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.ml import training


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    p = argparse.ArgumentParser()
    p.add_argument("--assess", action="store_true", help="only print historical coverage")
    p.add_argument("--no-xgboost", action="store_true")
    p.add_argument("--no-random-forest", action="store_true", help="faster: baselines + XGBoost only (ADR-023)")
    args = p.parse_args(argv)
    s = get_settings()
    if not s.market_prices_path.exists():
        print("market_prices.parquet missing. Run scripts.fetch_official_data and scripts.preprocess_data first.")
        return 1

    cov = training.assess_coverage(pd.read_parquet(s.market_prices_path))
    print(f"series: {len(cov)}, eligible (>= {training.MIN_OBSERVATIONS} clean obs): {int(cov['eligible'].sum())}")
    print(cov.head(20).to_string(index=False))
    if args.assess:
        return 0

    candidates = tuple(c for c, off in (("random_forest", args.no_random_forest), ("xgboost", args.no_xgboost)) if not off)
    try:
        meta = training.train(s.market_prices_path, s.models_dir, candidates)
    except training.InsufficientHistory as exc:
        print(f"INSUFFICIENT DATA: {exc}")
        return 2
    summary = {name: {"validation_mae": r["validation"]["mae"], "test_mae": r["test"]["mae"],
                      "test_dir_acc": r["test"]["directional_accuracy"]} for name, r in meta["results"].items()}
    print(json.dumps({"model_version": meta["model_version"], "selected": meta["selected_model"],
                      "split": meta["split"], "results": summary, "interval": meta["interval"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
