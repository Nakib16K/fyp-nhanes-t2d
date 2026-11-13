"""Privacy and explanation source contracts; no model deserialisation."""
from pathlib import Path
import ast

ROOT=Path(__file__).resolve().parents[1]

def test_api_and_training_contracts():
    api=(ROOT/'api/main.py').read_text(encoding='utf-8')
    pipeline=(ROOT/'src/pipeline.py').read_text(encoding='utf-8')
    ast.parse(api)
    assert 'classify_probability(prob, thresholds[model_name])' in api
    assert 'ready, rejected = choose_latest_complete(REPORTS_DIR)' in api
    assert 'LOCAL_EXPLANATION_SCOPE' in api
    assert 'allow_origins=allowed_origins(os.getenv("FYP_CORS_ORIGINS"))' in api
    assert 'allow_origins=["*"]' not in api
    assert 'traceback.print_exc()' not in api
    assert 'choose_validation_threshold(y_validation, validation_proba)' in pipeline
    assert 'best_f1 = f1_score(y_test, y_pred, zero_division=0)' in pipeline


def test_frontend_disclosures():
    local=(ROOT/'frontend/src/components/Exploratory/SHAPVisualization.tsx').read_text(encoding='utf-8')
    global_=(ROOT/'frontend/src/components/ModelComparison/ModelCard.tsx').read_text(encoding='utf-8')
    hook=(ROOT/'frontend/src/hooks/useAsync.ts').read_text(encoding='utf-8')
    assert 'uncalibrated' in local and 'not an explanation of the calibrated probability' in local
    assert 'underlying uncalibrated estimator' in global_
    assert 'taskRef.current' in hook and '[immediate]' in hook
