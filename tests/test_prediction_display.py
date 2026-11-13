"""Prediction display contracts: full-precision decision margins and one-hot display metadata.

Synthetic-only tests; no model pickle, NHANES dataset, network or AWS/Git.
"""
from unittest.mock import MagicMock
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
import api.main as api

INPUT = {
    'age_years':55, 'gender_code':1, 'ethnicity_code':7, 'education_level':3,
    'poverty_ratio':5.0, 'height_cm':222.0, 'weight_kg':122.0,
    'waist_circumference':100.0, 'systolic_bp':120, 'diastolic_bp':77,
    'pulse_60s':77, 'smoked_100_cigs':1, 'vigorous_activity':2,
    'family_history_diabetes':1, 'history_high_bp':1,
}


def test_margin_classification_uses_unrounded_probability():
    # This rounds to 0.2768 in the old API yet is above cutoff 0.2768058.
    prob, cutoff = 0.276811, 0.27680580621903694
    mock = MagicMock()
    mock.predict_proba.return_value = [[1-prob, prob]]
    previous = api.ml_registry.copy()
    try:
        api.ml_registry.update({'models': {'LR': mock}, 'metrics': [{'Model': 'LR', 'AUC': .8}],
                                'thresholds': {'LR': cutoff}, 'latest_run_dir': None,
                                'active_run_id': None})
        with TestClient(api.app) as client:
            r = client.post('/api/exploratory/predict/custom', json=INPUT)
        assert r.status_code == 200, r.text
        p = r.json()['predictions']['LR']
        assert p['probability_score'] == 0.2768
        assert p['above_threshold'] is True
        assert p['prediction_class'] == 'High Risk'  # backwards compatibility
        assert 0 < p['decision_margin_pp'] < 0.001
        assert p['decision_threshold'] == round(cutoff, 6)
    finally:
        api.ml_registry.clear()
        api.ml_registry.update(previous)


def test_shap_one_hot_indicator_status_labels_absence(monkeypatch):
    names=['ethnicity_code_3.0', 'ethnicity_code_7.0', 'age_years']
    preproc=MagicMock()
    preproc.transform.return_value=pd.DataFrame([[0.0,1.0,0.3]],columns=names)
    preproc.feature_names_out=names
    raw=MagicMock()
    raw.named_steps={'preprocessor':preproc,'model':MagicMock()}
    ens=MagicMock()
    ens.calibrated_classifiers_=[MagicMock(estimator=raw)]
    explainer=MagicMock()
    explainer.shap_values.return_value=np.array([[0.2,-0.5,0.1]])
    explainer.expected_value=0.0
    monkeypatch.setattr(api.shap,'TreeExplainer',lambda model:explainer)
    previous=api.ml_registry.copy()
    try:
        api.ml_registry.update({'models':{'XGB':ens},'metrics':[{'Model':'XGB','AUC':.8}],
                                'latest_run_dir':None,'thresholds':{}})
        with TestClient(api.app) as client:
            r=client.post('/api/exploratory/predict/custom/shap/XGB',json=INPUT)
        assert r.status_code == 200, r.text
        d=r.json()['shap_values_sorted']
        states={item['feature']:item.get('indicator_state') for item in d}
        assert states['Ethnicity: Non-Hispanic White']=='absent'
        assert states['Ethnicity: Other Race (including Multi-Racial)']=='present'
        assert states['Age (years)'] is None
        assert r.json()['explains_calibrated_probability'] is False
    finally:
        api.ml_registry.clear()
        api.ml_registry.update(previous)


def test_frontend_refuses_clinical_cutoff_implication():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    custom=(root/'frontend/src/components/Exploratory/ModelDecisionExplanation.tsx').read_text()
    preset=(root/'frontend/src/components/Exploratory/PresetCard.tsx').read_text()
    shap=(root/'frontend/src/components/Exploratory/SHAPVisualization.tsx').read_text()
    assert 'prediction.above_threshold' in custom
    assert 'decision_margin_pp' in custom
    assert 'Illustrative arithmetic mean of four model estimates' in preset
    assert 'not a medical cutoff' in preset
    assert 'indicatorState' in shap and 'featureData.slice(0, 5)' in shap
