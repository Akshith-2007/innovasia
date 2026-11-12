"""Re-derive test metrics from the saved test predictions and check they match model metadata.

    python -m scripts.evaluate_model
Exit code 1 on mismatch (artifact tampering or non-reproducible evaluation).
"""

from __future__ import annotations

import math
import sys

import pandas as pd

from app.core.config import get_settings
from app.ml.features import price_metrics
from app.ml.metadata import current_version, model_dir, read_metadata


def main() -> int:
    s = get_settings()
    version = current_version(s.models_dir)
    if not version:
        print("No trained model. Run scripts.train_price_model first.")
        return 1
    meta = read_metadata(s.models_dir, version)
    preds = pd.read_parquet(model_dir(s.models_dir, version) / "test_predictions.parquet")
    last, actual = preds["modal_price"].to_numpy(), preds["target_price"].to_numpy()
    ok = True
    print(f"model {version}  selected={meta['selected_model']}  test rows={len(preds)}")
    print(f"{'model':<18}{'MAE':>10}{'RMSE':>10}{'MAPE%':>8}{'DirAcc':>8}")
    for name, res in meta["results"].items():
        m = price_metrics(last, actual, preds[f"pred_{name}"].to_numpy())
        for key in ("mae", "rmse"):
            if not math.isclose(m[key], res["test"][key], rel_tol=1e-9):
                ok = False
                print(f"MISMATCH {name}.{key}: recomputed {m[key]} vs stored {res['test'][key]}")
        da = m["directional_accuracy"]
        print(f"{name:<18}{m['mae']:>10.1f}{m['rmse']:>10.1f}{(m['mape'] or float('nan')):>8.2f}"
              f"{(da if da is not None else float('nan')):>8.3f}")
    print("metrics reproduce stored metadata" if ok else "METRICS DO NOT MATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
