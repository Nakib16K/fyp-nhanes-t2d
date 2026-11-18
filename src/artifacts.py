"""Deterministic run-specific artifact inventory and validation.

Uses only the Python standard library. A manifest proves that the local files
are internally consistent, NOT that untrusted pickle contents are safe to load.
Never load joblib/pickle files from an untrusted source.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
from typing import Any

MODELS = ("lr", "rf", "lgbm", "xgb")
MANIFEST_NAME = "f1c_manifest.json"
SCHEMA = "fyp-f1c-run-v1"


class ArtifactError(ValueError):
    """A run's artifacts or metadata are missing, unsafe, or inconsistent."""


def _inside(run: Path, path: str) -> Path:
    if not isinstance(path, str) or not path or "\\" in path:
        raise ArtifactError(f"Bad relative artifact path: {path!r}")
    part = Path(path)
    if part.is_absolute() or PurePosixPath(path).is_absolute() or ".." in part.parts or "." in part.parts:
        raise ArtifactError(f"Unsafe artifact path: {path!r}")
    candidate = run / part
    if not candidate.is_file() or any(p.is_symlink() for p in [candidate, *candidate.parents] if p != run.parent):
        raise ArtifactError(f"Artifact missing or symlinked: {path!r}")
    if not candidate.resolve().is_relative_to(run.resolve()):
        raise ArtifactError(f"Artifact escapes run directory: {path!r}")
    return candidate


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def entry(run: Path, name: str) -> dict[str, str]:
    path = _inside(run, name)
    if path.stat().st_size == 0:
        raise ArtifactError(f"Artifact empty: {name}")
    return {"path": name, "sha256": sha256(path)}


def _read_metrics(run: Path) -> dict[str, dict[str, str]]:
    csv_path = _inside(run, "summary_metrics.csv")
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        required = {"Model", "AUC", "Best_Threshold", "Threshold_Source", "Validation_F1"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ArtifactError("Metrics CSV lacks threshold-provenance fields")
        data = {}
        for row in reader:
            model = (row.get("Model") or "").lower()
            if model not in MODELS or model in data:
                raise ArtifactError(f"Unknown or duplicate model in CSV: {model!r}")
            if row.get("Threshold_Source") != "validation":
                raise ArtifactError("CSV threshold provenance must be 'validation'")
            for field in ("Best_Threshold", "Validation_F1", "AUC"):
                try:
                    value = float(row.get(field, ""))
                except (TypeError, ValueError) as e:
                    raise ArtifactError(f"Bad CSV {field} for {model}") from e
                if not math.isfinite(value) or value < 0 or value > 1:
                    raise ArtifactError(f"Out-of-bounds CSV {field} for {model}")
            data[model] = row
        if set(data) != set(MODELS):
            raise ArtifactError(f"Expected four models in CSV, got {sorted(data)}")
        return data


def _thresholds(choices: dict[str, Any]) -> dict[str, dict[str, float | str]]:
    if set(choices) != set(MODELS):
        raise ArtifactError(f"Missing model threshold(s); expected {MODELS}")
    data = {}
    for model, selection in choices.items():
        origin = getattr(selection, "selected_from", None)
        threshold = float(getattr(selection, "threshold", float("nan")))
        val_f1 = float(getattr(selection, "validation_f1", float("nan")))
        if origin != "validation" or not math.isfinite(threshold) or not 0 <= threshold <= 1:
            raise ArtifactError(f"Invalid validation threshold for {model}")
        if not math.isfinite(val_f1) or not 0 <= val_f1 <= 1:
            raise ArtifactError(f"Invalid validation F1 for {model}")
        data[model] = {"threshold": threshold, "source": origin, "validation_f1": val_f1}
    return data


def _make(run: Path, balancing_method: str, choices: dict[str, Any], split: dict[str, int]) -> dict:
    if not run.name.startswith("run_") or balancing_method not in ("class_weight", "smote", "undersample"):
        raise ArtifactError("Expected a named run directory and known balancing strategy")
    if set(split) != {"train", "validation", "test"} or any(type(v) is not int or v <= 0 for v in split.values()):
        raise ArtifactError("Split counts must be positive integers")
    m = _read_metrics(run)
    thresholds = _thresholds(choices)
    models = {}
    shap_plots = {}
    interpretations = {}
    classification_reports = {}
    for name in MODELS:
        threshold = thresholds[name]
        if not math.isclose(threshold["threshold"], float(m[name]["Best_Threshold"]), rel_tol=1e-11, abs_tol=1e-11):
            raise ArtifactError(f"CSV and persisted {name} threshold disagree")
        if not math.isclose(threshold["validation_f1"], float(m[name]["Validation_F1"]), rel_tol=1e-11, abs_tol=1e-11):
            raise ArtifactError(f"CSV and persisted {name} validation F1 disagree")
        models[name] = {"artifact": entry(run, f"models/{name}_pipeline.pkl"), **threshold}
        shap_plots[name] = entry(run, f"{name}_shap_summary.png")
        interpretations[name] = entry(run, f"{name}_interpretation.txt")
        classification_reports[name] = entry(run, f"{name}_report.csv")
    return {
        "schema": SCHEMA,
        "run_id": run.name,
        "protocol": "post-dissertation-F1B-validation-threshold",
        "balancing_method": balancing_method,
        "sample_counts": split,
        "models": models,
        "metrics": entry(run, "summary_metrics.csv"),
        "fairness": entry(run, "algorithmic_fairness_report.csv"),
        "global_shap": shap_plots,
        "interpretations": interpretations,
        "classification_reports": classification_reports,
    }


def write_manifest(run_dir: str | Path, balancing_method: str, choices: dict[str, Any], split: dict[str, int]) -> Path:
    """Publish marker only after every required file exists and matches the CSV."""
    run = Path(run_dir).resolve()
    out = run / MANIFEST_NAME
    if out.exists():
        raise ArtifactError("Refusing to overwrite existing manifest")
    data = _make(run, balancing_method, choices, split)
    # Do not leave a partially written manifest marked ready.
    staging = run / f".{MANIFEST_NAME}.staging"
    if staging.exists():
        raise ArtifactError("Existing staging marker; inspect this run manually")
    try:
        with staging.open("x", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True, allow_nan=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(staging, out)
    except Exception:
        if staging.exists():
            staging.unlink()
        raise
    return out


def load_verified_run(run_dir: str | Path) -> dict:
    """Validate all named files and recorded CSV values without loading models."""
    run = Path(run_dir).resolve()
    manifest = _inside(run, MANIFEST_NAME)
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise ArtifactError(f"Invalid run manifest: {e}") from e
    if data.get("schema") != SCHEMA or data.get("run_id") != run.name:
        raise ArtifactError("Manifest schema/run identity mismatch")
    if (
        set(data.get("models", {})) != set(MODELS)
        or data.get("protocol") != "post-dissertation-F1B-validation-threshold"
    ):
        raise ArtifactError("Unrecognized model set or threshold protocol")
    if data.get("balancing_method") not in ("class_weight", "smote", "undersample"):
        raise ArtifactError("Unknown balancing method in manifest")
    counts = data.get("sample_counts")
    if (
        not isinstance(counts, dict)
        or set(counts) != {"train", "validation", "test"}
        or any(type(v) is not int or v <= 0 for v in counts.values())
    ):
        raise ArtifactError("Invalid split counts")

    def verify(item: Any):
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise ArtifactError("Malformed artifact entry")
        path = _inside(run, item["path"])
        if len(item["sha256"]) != 64 or sha256(path) != item["sha256"]:
            raise ArtifactError(f"Artifact checksum mismatch: {item['path']}")
        return path

    metrics_path = verify(data.get("metrics"))
    verify(data.get("fairness"))
    rows = _read_metrics(run)
    model_paths = {}
    for name in MODELS:
        e = data["models"][name]
        if not isinstance(e, dict) or set(e) != {"artifact", "threshold", "source", "validation_f1"}:
            raise ArtifactError(f"Invalid model manifest entry {name}")
        path = verify(e["artifact"])
        if e["artifact"]["path"] != f"models/{name}_pipeline.pkl":
            raise ArtifactError(f"Invalid run-specific model path {name}")
        t = e["threshold"]
        if not isinstance(t, (int, float)) or isinstance(t, bool) or not math.isfinite(t) or t < 0 or t > 1:
            raise ArtifactError(f"Invalid frozen threshold {name}")
        if e["source"] != "validation" or not math.isclose(
            t,
            float(rows[name]["Best_Threshold"]),
            rel_tol=1e-11,
            abs_tol=1e-11,
        ):
            raise ArtifactError(f"Threshold provenance/matching failed {name}")
        if not math.isclose(e["validation_f1"], float(rows[name]["Validation_F1"]), rel_tol=1e-11, abs_tol=1e-11):
            raise ArtifactError(f"Validation score mismatch {name}")
        model_paths[name.upper()] = path
    for section, fmt in (("global_shap", "{}_shap_summary.png"), ("interpretations", "{}_interpretation.txt"), ("classification_reports", "{}_report.csv")):
        if set(data.get(section, {})) != set(MODELS):
            raise ArtifactError(f"Missing model artifacts from {section}")
        for model in MODELS:
            if data[section][model].get("path") != fmt.format(model):
                raise ArtifactError(f"Unexpected {section} path for {model}")
            verify(data[section][model])
    return {
        "run_dir": run,
        "manifest": data,
        "model_paths": model_paths,
        "metrics_path": metrics_path,
        "metrics_rows": list(rows.values()),
    }


def choose_latest_complete(reports_root: str | Path) -> tuple[dict | None, list[str]]:
    """Select latest COMPLETE run. Report every skipped candidate for diagnostics."""
    root = Path(reports_root)
    if not root.exists():
        return None, []
    rejected = []
    for folder in sorted(root.glob("run_*"), reverse=True):
        if not folder.is_dir() or folder.is_symlink():
            continue
        try:
            return load_verified_run(folder), rejected
        except (ArtifactError, ValueError, TypeError, OSError, KeyError) as e:
            rejected.append(f"{folder.name}: {e}")
    return None, rejected
