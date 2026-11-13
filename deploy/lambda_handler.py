"""Lambda adapter: cold-start bootstrap once per execution environment.

The existing FastAPI lifespan loads four models on Uvicorn startup. Mangum's
lifespan='off' disables that startup, so we explicitly bootstrap verified models
once at module import instead. The recorded private image passed Linux/Lambda
parity; future builds and public hosting require separate acceptance.
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
    # Only trusted, separately checksum-pinned, locally created model binaries.
    loaded = {name: joblib.load(path) for name, path in ready["model_paths"].items()}
    thresholds = {
        name.upper(): entry["threshold"]
        for name, entry in ready["manifest"]["models"].items()
    }
    validate_model_thresholds(loaded, thresholds)
    metrics = pd.read_csv(ready["metrics_path"]).to_dict(orient="records")
    ml_registry.update(
        {
            "models": loaded,
            "metrics": metrics,
            "thresholds": thresholds,
            "latest_run_dir": str(ready["run_dir"]),
            "active_run_id": EXPECTED_RUN,
        }
    )


_bootstrap_once()
# Intentionally OFF: lifespan would unload/reload the ~280 MiB model set per invocation.
handler = Mangum(app, lifespan="off")
