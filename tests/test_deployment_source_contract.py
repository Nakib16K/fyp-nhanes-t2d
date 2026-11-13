from pathlib import Path
from src.security import deployment_config

ROOT=Path(__file__).resolve().parents[1]

def test_readonly_deployment_contract():
    src=(ROOT/'api'/'main.py').read_text(encoding='utf-8')
    assert 'BodyLimitMiddleware, max_body_bytes=8192' in src
    assert 'app.add_middleware(TrustedHostMiddleware' in src
    assert '"explains_calibrated_probability": False' in src
    assert 'classify_probability(prob, thresholds[model_name])' in src
    assert 'uvicorn.run(app, host="127.0.0.1", port=8000)' in src
    assert deployment_config({})['docs_enabled'] is True
    assert (ROOT/'docs'/'POST_SUBMISSION_DEVELOPMENT.md').is_file()
