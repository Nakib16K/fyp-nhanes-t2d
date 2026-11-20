"""Exercise the Lambda startup function with trusted synthetic artifacts."""
import ast
import hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.decisions import validate_model_thresholds


def bootstrap(tmp_path, background_loader):
    file = Path(__file__).resolve().parents[1] / 'deploy/lambda_handler.py'
    tree = ast.parse(file.read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_bootstrap_once')
    run = tmp_path / 'run_synthetic'
    run.mkdir()
    marker = run / 'f1c_manifest.json'
    marker.write_text('synthetic manifest')
    names = ['LR', 'RF', 'LGBM', 'XGB']
    metadata = {'run_id': run.name, 'models': {n.lower(): {'threshold': .3} for n in names}}
    ready = {'run_dir': run, 'manifest': metadata, 'model_paths': {n: run / (n + '.pkl') for n in names}, 'metrics_path': run / 'metrics.csv'}
    registry = {'models': {}, 'linear_background': None}
    namespace = {
        'Path': Path, 'hashlib': hashlib, 'REPORTS_DIR': str(tmp_path),
        'EXPECTED_RUN': run.name, 'EXPECTED_MANIFEST_SHA256': hashlib.sha256(marker.read_bytes()).hexdigest(),
        'choose_latest_complete': lambda _: (ready, []),
        'joblib': SimpleNamespace(load=lambda _: object()),
        'pd': SimpleNamespace(read_csv=lambda _: pd.DataFrame([{'Model': n} for n in names])),
        'validate_model_thresholds': validate_model_thresholds,
        'load_linear_background': background_loader, 'ml_registry': registry,
    }
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(file), 'exec'), namespace)
    return namespace['_bootstrap_once'], registry, ready


def test_lambda_startup_publishes_the_verified_lr_reference(tmp_path):
    reference = {'feature_names': ['a'], 'mean': [0.0], 'sample_count': 2}
    loader = MagicMock(return_value=reference)
    start, registry, ready = bootstrap(tmp_path, loader)
    start()
    loader.assert_called_once_with(ready['run_dir'], ready['manifest'])
    assert registry['linear_background'] is reference
    assert set(registry['models']) == {'LR', 'RF', 'LGBM', 'XGB'}


def test_lambda_reference_failure_leaves_no_partial_active_registry(tmp_path):
    start, registry, _ = bootstrap(tmp_path, MagicMock(side_effect=ValueError('bad reference')))
    with pytest.raises(ValueError, match='bad reference'):
        start()
    assert registry == {'models': {}, 'linear_background': None}
