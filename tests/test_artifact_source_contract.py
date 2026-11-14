"""Artifact source contracts against the current application."""
import ast
from pathlib import Path



def get_sources():
    root = Path(__file__).resolve().parents[1]
    pipeline = root / "src" / "pipeline.py"
    api = root / "api" / "main.py"
    return pipeline.read_text(encoding="utf-8"), api.read_text(encoding="utf-8")


def test_source_parses():
    p, a = get_sources()
    ast.parse(p)
    ast.parse(a)


def test_models_written_within_run_and_never_root():
    p, _ = get_sources()
    assert 'model_path = os.path.join(run_models_dir, f"{model_name}_pipeline.pkl")' in p
    assert 'model_path = os.path.join(MODELS_DIR, f"{model_name}_pipeline.pkl")' not in p


def test_manifest_written_after_metrics():
    p, _ = get_sources()
    assert p.index('write_manifest(\n            self.run_dir') > p.index('pd.DataFrame(results_summary).to_csv(')


def test_validation_threshold_pipeline_contract():
    p, _ = get_sources()
    assert 'choose_validation_threshold(y_validation, validation_proba)' in p
    assert '_optimize_threshold(' not in p
    assert 'selection = self.selected_thresholds.get(target_model)' in p


def test_no_legacy_model_loading_in_api():
    _, a = get_sources()
    assert 'glob.glob(os.path.join(MODELS_DIR, "*_pipeline.pkl"))' not in a
    assert 'ready, rejected = choose_latest_complete(REPORTS_DIR)' in a
    assert 'for name, path in ready["model_paths"].items()' in a


def test_api_reads_metrics_from_same_run():
    _, a = get_sources()
    assert 'pd.read_csv(ready["metrics_path"])' in a
    assert 'ml_registry.update({' in a
    assert '"active_run_id": meta["run_id"]' in a


def test_api_uses_verified_threshold():
    _, a = get_sources()
    assert 'classify_probability(prob, thresholds[model_name])' in a
    assert '"High Risk" if prob >= 0.5 else "Low Risk"' not in a
    assert '"thresholds": {name.upper(): meta["models"][name]["threshold"]' in a
