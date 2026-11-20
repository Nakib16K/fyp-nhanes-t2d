"""Load the verified model run when a Lambda environment starts.

Uvicorn loads models through the FastAPI lifespan. The Lambda adapter disables
that lifespan in Mangum and loads the models on import. Later invocations reuse
the loaded models.
"""
from __future__ import annotations

from pathlib import Path
import hashlib

import joblib
import pandas as pd
from mangum import Mangum

from api.main import app, ml_registry, REPORTS_DIR
from src.artifacts import choose_latest_complete
from src.decisions import validate_model_thresholds
from src.linear_shap import load_linear_background

EXPECTED_RUN = "run_f1f2_2026-11-09_16-22-47_574130"
EXPECTED_MANIFEST_SHA256 = "f5bb0b3cbcec5266b2894e52cfce0b7b2434e3dee687e6d730e6301a28b56475"


def _bootstrap_once():
    root = Path(REPORTS_DIR)
    folders = list(root.glob("run_*"))
    if len(folders) != 1 or folders[0].name != EXPECTED_RUN:
        raise RuntimeError("Container run inventory does not match the approved run")
    manifest_file = folders[0] / "f1c_manifest.json"
    if (
        not manifest_file.is_file()
        or hashlib.sha256(manifest_file.read_bytes()).hexdigest()
        != EXPECTED_MANIFEST_SHA256
    ):
        raise RuntimeError("Frozen manifest verification failed")
    ready, rejected = choose_latest_complete(root)
    if ready is None or rejected or ready["manifest"]["run_id"] != EXPECTED_RUN:
        raise RuntimeError("Frozen artifact verification failed")
    # The run checksums were verified before loading these model files.
    loaded = {name: joblib.load(path) for name, path in ready["model_paths"].items()}
    thresholds = {
        name.upper(): entry["threshold"]
        for name, entry in ready["manifest"]["models"].items()
    }
    validate_model_thresholds(loaded, thresholds)
    linear_background = load_linear_background(ready["run_dir"], ready["manifest"])
    metrics = pd.read_csv(ready["metrics_path"]).to_dict(orient="records")
    ml_registry.update(
        {
            "models": loaded,
            "metrics": metrics,
            "thresholds": thresholds,
            "latest_run_dir": str(ready["run_dir"]),
            "active_run_id": EXPECTED_RUN,
            "linear_background": linear_background,
        }
    )


_bootstrap_once()
handler = Mangum(app, lifespan="off")
