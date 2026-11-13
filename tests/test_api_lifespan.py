"""API lifecycle checks using synthetic manifests and mocked model load.

No real pickle deserialization, NHANES downloads, or full model training.
"""
import csv
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


def _context():
    try:
        import api.main as api
        from src.artifacts import write_manifest, MODELS
        from fastapi.testclient import TestClient
    except ImportError:
        pytest.skip("Requires installed project source and FastAPI deps")
    return api,write_manifest,MODELS,TestClient


def _run(root:Path, write_manifest, models, name="run_2026-11-08_11-30-00_123456"):
    run=root/name
    (run/"models").mkdir(parents=True)
    for model in models:
        (run/"models"/f"{model}_pipeline.pkl").write_bytes(b"DUMMY BINARY; DO NOT UNPICKLE")
        (run/f"{model}_shap_summary.png").write_bytes(b"PNG TEST IMAGE")
        (run/f"{model}_interpretation.txt").write_text("Interpretation")
        (run/f"{model}_report.csv").write_text("label,support\n0,1\n")
    (run/"algorithmic_fairness_report.csv").write_text("Group,FNR\nA,0.2\n")
    with (run/"summary_metrics.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=["Model","AUC","F1_Score","Precision","Recall_Sensitivity","Accuracy","Best_Threshold","Threshold_Source","Validation_F1"])
        writer.writeheader()
        for model in models:
            writer.writerow(dict(Model=model.upper(),AUC=0.84,F1_Score=0.56,Precision=0.48,Recall_Sensitivity=0.67,Accuracy=0.82,Best_Threshold=0.28,Threshold_Source="validation",Validation_F1=0.55))
    choices={model:SimpleNamespace(threshold=0.28,selected_from="validation",validation_f1=0.55) for model in models}
    write_manifest(run,"class_weight",choices,{"train":10084,"validation":2521,"test":3152})
    return run


def _clear(api):
    api.ml_registry.update({"models":{},"metrics":[],"latest_run_dir":None,"thresholds":{},"active_run_id":None})


def test_startup_loads_only_one_verified_run_and_matching_metrics(tmp_path,monkeypatch):
    api,write_manifest,models,Client=_context()
    _clear(api)
    run=_run(tmp_path,write_manifest,models)
    loaded=[]
    def fake_joblib(path):
        loaded.append(str(path))
        result=MagicMock()
        result.predict_proba.return_value=[[0.4,0.6]]
        return result
    monkeypatch.setattr(api,"REPORTS_DIR",str(tmp_path))
    monkeypatch.setattr(api.joblib,"load",fake_joblib)
    with Client(api.app) as client:
        assert set(client.get("/health").json()["models_loaded"])=={"LR","RF","LGBM","XGB"}
        assert len(client.get("/api/models/metrics").json())==4
        assert api.ml_registry["active_run_id"]==run.name
        assert api.ml_registry["thresholds"]["XGB"]==0.28
        assert all(str(run/"models") in p for p in loaded)
        assert all("/legacy_models/" not in p for p in loaded)
    assert api.ml_registry["models"]=={}
    assert api.ml_registry["active_run_id"] is None


def test_corrupt_latest_run_is_skipped_for_older_complete(tmp_path,monkeypatch):
    api,write_manifest,models,Client=_context()
    _clear(api)
    older=_run(tmp_path,write_manifest,models)
    newer=_run(tmp_path,write_manifest,models,"run_2026-11-09_00-00-00_000001")
    (newer/"models"/"xgb_pipeline.pkl").write_bytes(b"CHANGED AFTER MANIFEST")
    monkeypatch.setattr(api,"REPORTS_DIR",str(tmp_path))
    monkeypatch.setattr(api.joblib,"load",lambda path: MagicMock())
    with Client(api.app) as client:
        assert api.ml_registry["active_run_id"]==older.name
        assert len(client.get("/health").json()["models_loaded"])==4


def test_if_no_complete_run_never_falls_back_to_global_models(tmp_path,monkeypatch):
    api,write_manifest,models,Client=_context()
    _clear(api)
    (tmp_path/"run_2026-11-09_00-00-00").mkdir()
    monkeypatch.setattr(api,"REPORTS_DIR",str(tmp_path))
    monkeypatch.setattr(api.joblib,"load",lambda path: pytest.fail("Should not deserialize anything"))
    # Production must refuse startup when no verified model run exists.
    with pytest.raises(RuntimeError, match="no complete verified model run"):
        with Client(api.app):
            pytest.fail("Startup unexpectedly accepted a missing model run")
    assert api.ml_registry["models"]=={}
    assert api.ml_registry["active_run_id"] is None


def test_model_deserialization_failure_is_atomic(tmp_path,monkeypatch):
    api,write_manifest,models,Client=_context()
    _clear(api)
    _run(tmp_path,write_manifest,models)
    monkeypatch.setattr(api,"REPORTS_DIR",str(tmp_path))
    def fail_load(path):
        if "lgbm" in str(path):
            raise RuntimeError("Simulated model format mismatch")
        return MagicMock()
    monkeypatch.setattr(api.joblib,"load",fail_load)
    # Deserialization failure must abort startup and leave no partial model set.
    with pytest.raises(RuntimeError, match="verified model set could not be loaded"):
        with Client(api.app):
            pytest.fail("Startup unexpectedly accepted partially loaded models")
    assert api.ml_registry["models"]=={}
    assert api.ml_registry["active_run_id"] is None


def test_preserves_preseeded_mock_models_like_original_31_tests(tmp_path,monkeypatch):
    api,write_manifest,models,Client=_context()
    _clear(api)
    api.ml_registry["models"]={"XGB":MagicMock()}
    api.ml_registry["metrics"]=[{"Model":"XGB","AUC":0.8}]
    api.ml_registry["latest_run_dir"]=None
    monkeypatch.setattr(api,"REPORTS_DIR",str(tmp_path))
    with Client(api.app) as client:
        assert client.get("/health").json()["models_loaded"]==["XGB"]
    assert api.ml_registry["models"]=={}


def test_uses_run_bound_threshold_instead_of_half(tmp_path,monkeypatch):
    api,write_manifest,models,Client=_context()
    _clear(api)
    _run(tmp_path,write_manifest,models)
    monkeypatch.setattr(api,"REPORTS_DIR",str(tmp_path))
    def model(_):
        x=MagicMock()
        x.predict_proba.return_value=[[0.60,0.40]]
        return x
    monkeypatch.setattr(api.joblib,"load",model)
    payload={
        "age_years":45,"gender_code":1,"ethnicity_code":3,"education_level":3,
        "poverty_ratio":2.5,"height_cm":175.0,"weight_kg":85.0,
        "waist_circumference":95.0,"systolic_bp":128,"diastolic_bp":82,
        "pulse_60s":72,"smoked_100_cigs":1,
        "vigorous_activity":2,"family_history_diabetes":1,"history_high_bp":1,
    }
    with Client(api.app) as client:
        assert api.ml_registry["thresholds"]["XGB"]==0.28
        response=client.post("/api/exploratory/predict/custom",json=payload)
        assert response.status_code==200
        assert response.json()["predictions"]["XGB"]["prediction_class"]=="High Risk"
        assert response.json()["predictions"]["XGB"]["decision_threshold"]==0.28
        assert response.json()["predictions"]["XGB"]["threshold_source"]=="validation"
