"""Artifact protocol tests, independent of real NHANES data and pickle loading."""
import csv
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.artifacts import (
    ArtifactError, MANIFEST_NAME, MODELS, choose_latest_complete,
    load_verified_run, write_manifest,
)

FIELDS = ["Model", "AUC", "Best_Threshold", "Threshold_Source", "Validation_F1"]


def make_run(root: Path, suffix="run_2026-11-08_11-30-00_000001", *, models=MODELS):
    run = root / suffix
    (run / "models").mkdir(parents=True)
    for i, model in enumerate(models):
        (run / "models" / f"{model}_pipeline.pkl").write_bytes(f"DUMMY-NOT-A-PICKLE-{model}".encode())
        (run / f"{model}_shap_summary.png").write_bytes(b"DUMMY PNG\x89" + model.encode())
        (run / f"{model}_interpretation.txt").write_text("test interpretation", encoding="utf-8")
        (run / f"{model}_report.csv").write_text("label,metric\n0,0.5\n", encoding="utf-8")
    (run / "algorithmic_fairness_report.csv").write_text("Group,FNR\nA,0.2\n", encoding="utf-8")
    with (run / "summary_metrics.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for i, model in enumerate(models):
            writer.writerow({"Model":model.upper(),"AUC":0.80+i*0.01,"Best_Threshold":0.24+i*0.01,"Threshold_Source":"validation","Validation_F1":0.54+i*0.01})
    choices = {model:SimpleNamespace(threshold=0.24+i*0.01, validation_f1=0.54+i*0.01,selected_from="validation") for i,model in enumerate(models)}
    return run, choices


def make_complete(root: Path, suffix="run_2026-11-08_11-30-00_000001"):
    run, sel = make_run(root, suffix)
    write_manifest(run,"class_weight",sel,{"train":10084,"validation":2521,"test":3152})
    return run


def test_roundtrip_manifest_and_four_models(tmp_path):
    run=make_complete(tmp_path)
    found=load_verified_run(run)
    assert found["manifest"]["run_id"]==run.name
    assert set(found["model_paths"])=={"LR","RF","LGBM","XGB"}
    assert found["manifest"]["sample_counts"]["test"]==3152
    assert len(found["metrics_rows"])==4


def test_no_complete_run_yet(tmp_path):
    assert choose_latest_complete(tmp_path)==(None,[])


def test_latest_complete_skips_newer_incomplete(tmp_path):
    older=make_complete(tmp_path)
    newer=tmp_path/"run_2026-11-09_00-00-00_000001"
    newer.mkdir()
    found, rejected=choose_latest_complete(tmp_path)
    assert found["run_dir"]==older
    assert len(rejected)==1 and "run_2026-11-09" in rejected[0]


def test_verify_detects_model_bytes_changed(tmp_path):
    run=make_complete(tmp_path)
    with (run/"models"/"xgb_pipeline.pkl").open("ab") as f: f.write(b"altered")
    with pytest.raises(ArtifactError,match="checksum"):
        load_verified_run(run)


def test_verify_detects_metrics_changed(tmp_path):
    run=make_complete(tmp_path)
    with (run/"summary_metrics.csv").open("a") as f: f.write("extra,row\n")
    with pytest.raises(ArtifactError,match="checksum"):
        load_verified_run(run)


def test_manifest_not_published_when_shap_missing(tmp_path):
    run,sel=make_run(tmp_path)
    (run/"rf_shap_summary.png").unlink()
    with pytest.raises(ArtifactError,match="missing"):
        write_manifest(run,"class_weight",sel,{"train":10084,"validation":2521,"test":3152})
    assert not (run/MANIFEST_NAME).exists()


def test_manifest_not_published_when_fairness_missing(tmp_path):
    run,sel=make_run(tmp_path)
    (run/"algorithmic_fairness_report.csv").unlink()
    with pytest.raises(ArtifactError): write_manifest(run,"class_weight",sel,{"train":10084,"validation":2521,"test":3152})
    assert not (run/MANIFEST_NAME).exists()


def test_invalid_threshold_provenance_rejected(tmp_path):
    run,sel=make_run(tmp_path)
    sel["xgb"].selected_from="test"
    with pytest.raises(ArtifactError,match="validation threshold"):
        write_manifest(run,"class_weight",sel,{"train":10084,"validation":2521,"test":3152})


def test_disagreeing_csv_threshold_rejected(tmp_path):
    run,sel=make_run(tmp_path)
    sel["xgb"].threshold=0.999
    with pytest.raises(ArtifactError,match="disagree"):
        write_manifest(run,"class_weight",sel,{"train":10084,"validation":2521,"test":3152})


def test_no_duplicate_published_manifest(tmp_path):
    run=make_complete(tmp_path)
    sel={model:SimpleNamespace(threshold=0.24+i*0.01,validation_f1=0.54+i*0.01,selected_from="validation") for i,model in enumerate(MODELS)}
    with pytest.raises(ArtifactError,match="overwrite"):
        write_manifest(run,"class_weight",sel,{"train":10084,"validation":2521,"test":3152})


def test_manifest_run_identity_checked(tmp_path):
    run=make_complete(tmp_path)
    info=json.loads((run/MANIFEST_NAME).read_text())
    info["run_id"]="run_2026-04-07_12-41-24"
    (run/MANIFEST_NAME).write_text(json.dumps(info))
    with pytest.raises(ArtifactError,match="identity"):
        load_verified_run(run)


def test_manifest_artifact_traversal_rejected(tmp_path):
    run=make_complete(tmp_path)
    info=json.loads((run/MANIFEST_NAME).read_text())
    info["models"]["xgb"]["artifact"]["path"]="../../escape.pkl"
    (run/MANIFEST_NAME).write_text(json.dumps(info))
    with pytest.raises(ArtifactError,match="Unsafe"):
        load_verified_run(run)


def test_manifest_absolute_path_rejected(tmp_path):
    run=make_complete(tmp_path)
    info=json.loads((run/MANIFEST_NAME).read_text())
    info["models"]["rf"]["artifact"]["path"]="/etc/hosts"
    (run/MANIFEST_NAME).write_text(json.dumps(info))
    with pytest.raises(ArtifactError,match="Unsafe"):
        load_verified_run(run)


def test_missing_csv_model_rejected(tmp_path):
    run,sel=make_run(tmp_path,models=MODELS[:3])
    with pytest.raises(ArtifactError,match="four models"):
        write_manifest(run,"class_weight",sel,{"train":10084,"validation":2521,"test":3152})


def test_invalid_split_count_rejected(tmp_path):
    run,sel=make_run(tmp_path)
    with pytest.raises(ArtifactError,match="Split counts"):
        write_manifest(run,"class_weight",sel,{"train":10084,"validation":0,"test":3152})


def test_older_legacy_global_models_not_considered(tmp_path):
    (tmp_path.parent/"models").mkdir(exist_ok=True)
    (tmp_path.parent/"models"/"xgb_pipeline.pkl").write_text("legacy")
    found,issues=choose_latest_complete(tmp_path)
    assert found is None


def test_not_ready_run_with_only_summary_is_skipped(tmp_path):
    run,sel=make_run(tmp_path)
    found,issues=choose_latest_complete(tmp_path)
    assert found is None and len(issues)==1


def test_tampered_shap_image_rejected(tmp_path):
    run=make_complete(tmp_path)
    (run/"lr_shap_summary.png").write_bytes(b"changed")
    with pytest.raises(ArtifactError,match="checksum"):
        load_verified_run(run)


def test_modified_csv_provenance_rejected_without_manifest(tmp_path):
    run,sel=make_run(tmp_path)
    csv=run/"summary_metrics.csv"
    txt=csv.read_text().replace("validation","test")
    csv.write_text(txt)
    with pytest.raises(ArtifactError,match="provenance"):
        write_manifest(run,"class_weight",sel,{"train":10084,"validation":2521,"test":3152})


def test_missing_interpretation_rejected(tmp_path):
    run,sel=make_run(tmp_path)
    (run/"xgb_interpretation.txt").unlink()
    with pytest.raises(ArtifactError,match="missing"):
        write_manifest(run,"class_weight",sel,{"train":10084,"validation":2521,"test":3152})


def test_manifest_not_written_when_staging_exists(tmp_path):
    run,sel=make_run(tmp_path)
    (run/f".{MANIFEST_NAME}.staging").write_text("partial")
    with pytest.raises(ArtifactError,match="staging"):
        write_manifest(run,"class_weight",sel,{"train":10084,"validation":2521,"test":3152})


def test_symlink_is_rejected_if_supported(tmp_path):
    run,sel=make_run(tmp_path)
    target=run/"rf_shap_summary.png"
    target.unlink()
    try:
        target.symlink_to(run/"lr_shap_summary.png")
    except (OSError,NotImplementedError):
        pytest.skip("Symlinks not available in this environment")
    with pytest.raises(ArtifactError,match="symlink"):
        write_manifest(run,"class_weight",sel,{"train":10084,"validation":2521,"test":3152})
