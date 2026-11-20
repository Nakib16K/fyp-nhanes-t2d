"""Check research wiring without running training, downloads or persistence."""
import ast
from pathlib import Path


def _method(name):
    source = Path(__file__).resolve().parents[1] / 'src/pipeline.py'
    trainer = next(n for n in ast.parse(source.read_text(encoding='utf-8')).body
                   if isinstance(n, ast.ClassDef) and n.name == 'ModelTrainer')
    return next(n for n in trainer.body if isinstance(n, ast.FunctionDef) and n.name == name)


def _calls(tree, name):
    return [n for n in ast.walk(tree) if isinstance(n, ast.Call)
            and ((isinstance(n.func, ast.Name) and n.func.id == name)
                 or (isinstance(n.func, ast.Attribute) and n.func.attr == name))]


def _assigned(tree, name):
    return next(n.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))


def test_original_holdout_and_validation_splits():
    splits = _calls(_method('run'), 'train_test_split')
    assert [[ast.unparse(a) for a in call.args] for call in splits] == [
        ['X', 'y'], ['X_train', 'y_train'],
    ]
    for call, stratify in zip(splits, ['y', 'y_train']):
        keywords = {k.arg: k.value for k in call.keywords}
        assert ast.literal_eval(keywords['test_size']) == .2
        assert ast.literal_eval(keywords['random_state']) == 42
        assert ast.unparse(keywords['stratify']) == stratify


def test_fitting_and_cross_validation_use_only_fit_records():
    run = _method('run')
    assert [[ast.unparse(a) for a in c.args] for c in _calls(run, 'fit')] == [
        ['X_fit', 'y_fit'], ['X_fit', 'y_fit'],
    ]
    cv = _calls(run, 'cross_val_score')
    assert len(cv) == 1
    assert [ast.unparse(a) for a in cv[0].args] == ['pipeline', 'X_fit', 'y_fit']
    assert {k.arg: ast.unparse(k.value) for k in cv[0].keywords}['cv'] == 'cv_split'


def test_threshold_is_selected_on_validation_before_fixed_test_decision():
    run = _method('run')
    predictions = {ast.unparse(c.args[0]) for c in _calls(run, 'predict_proba')}
    assert predictions == {'X_validation', 'X_test'}
    selected = _calls(run, 'choose_validation_threshold')
    assert len(selected) == 1
    assert [ast.unparse(a) for a in selected[0].args] == ['y_validation', 'validation_proba']
    assert ast.unparse(_assigned(run, 'best_thresh')) == 'threshold_choice.threshold'
    assert ast.unparse(_assigned(run, 'y_pred')) == 'classify_at_threshold(y_proba, best_thresh)'
    f1 = _assigned(run, 'best_f1')
    assert [ast.unparse(a) for a in f1.args] == ['y_test', 'y_pred']
    assert not _calls(run, '_optimize_threshold')


def test_models_and_completed_manifest_stay_with_the_run():
    run = _method('run')
    assert ast.unparse(_assigned(run, 'run_models_dir')) == "os.path.join(self.run_dir, 'models')"
    assert ast.unparse(_assigned(run, 'model_path')) == 'os.path.join(run_models_dir, f\'{model_name}_pipeline.pkl\')'
    saved = [call for call in _calls(run, 'dump') if ast.unparse(call.func) == 'joblib.dump']
    assert len(saved) == 1
    assert [ast.unparse(a) for a in saved[0].args] == ['calibrated_model', 'model_path']
    manifest = _calls(run, 'write_manifest')
    assert len(manifest) == 1
    assert [ast.unparse(a) for a in manifest[0].args[:3]] == [
        'self.run_dir', 'balancing_method', 'self.selected_thresholds',
    ]
    assert all(call.lineno < manifest[0].lineno for call in _calls(run, 'to_csv'))
    cache = _assigned(run, 'cache_path')
    assert any(isinstance(n, ast.Constant) and n.value == '_f1b_train64_seed42.json'
               for n in ast.walk(cache))


def test_fairness_uses_the_already_selected_threshold():
    method = _method('_generate_fairness_report')
    assert ast.unparse(_assigned(method, 'selection')) == 'self.selected_thresholds.get(target_model)'
    calls = _calls(method, 'subgroup_fairness')
    assert len(calls) == 1
    assert [ast.unparse(a) for a in calls[0].args] == [
        'y_test', 'y_proba', 'X_test[column].to_numpy()', 'selection',
    ]
    assert not _calls(method, 'choose_validation_threshold')
