"""Synthetic acquisition failures must stop future research ingestion."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

import src.data_loader as module


@pytest.fixture
def loader(tmp_path, monkeypatch):
    monkeypatch.setattr(module, 'RAW_DATA_PATH', str(tmp_path))
    monkeypatch.setattr(module, 'NHANES_FILE_MANIFEST', {'cycle': {'DEMO': 'DEMO.xpt', 'BMX': 'BMX.xpt'}})
    monkeypatch.setattr(module, 'BASE_URLS', {'cycle': 'https://offline.invalid'})
    return module.NHANESDataLoader()


def response(content=b'synthetic raw bytes'):
    return SimpleNamespace(content=content, raise_for_status=lambda: None)


def test_failed_download_never_reports_integrity_pass(loader, monkeypatch, capsys):
    download = Mock(side_effect=RuntimeError('synthetic unavailable response'))
    monkeypatch.setattr(module.requests, 'get', download)
    with pytest.raises(RuntimeError, match='Required NHANES downloads unavailable'):
        loader.download_data()
    assert download.call_count == 2
    assert 'passed' not in capsys.readouterr().out.lower()
    assert list(Path(loader.raw_path).iterdir()) == []


def test_download_failures_are_aggregated_after_other_attempts(loader, monkeypatch):
    download = Mock(side_effect=[RuntimeError('synthetic failure'), response()])
    monkeypatch.setattr(module.requests, 'get', download)
    with pytest.raises(RuntimeError, match='cycle/DEMO.xpt'):
        loader.download_data()
    assert download.call_count == 2
    assert not (Path(loader.raw_path) / 'DEMO.xpt').exists()
    assert (Path(loader.raw_path) / 'BMX.xpt').read_bytes() == b'synthetic raw bytes'


def test_empty_download_cannot_become_a_required_raw_file(loader, monkeypatch):
    monkeypatch.setattr(module.requests, 'get', lambda * args, **kwargs: response(b''))
    with pytest.raises(RuntimeError, match='Required NHANES downloads unavailable'):
        loader.download_data()
    assert list(Path(loader.raw_path).iterdir()) == []


def test_existing_nonempty_files_do_not_trigger_downloads(loader, monkeypatch):
    for name in ['DEMO.xpt', 'BMX.xpt']:
        (Path(loader.raw_path) / name).write_bytes(b'existing synthetic input')
    download = Mock(side_effect=AssertionError('No download expected'))
    monkeypatch.setattr(module.requests, 'get', download)
    loader.download_data()
    download.assert_not_called()


def test_existing_empty_file_is_replaced_after_successful_download(loader, monkeypatch):
    for name in ['DEMO.xpt', 'BMX.xpt']:
        (Path(loader.raw_path) / name).write_bytes(b'')
    monkeypatch.setattr(module.requests, 'get', lambda * args, **kwargs: response())
    loader.download_data()
    assert all(path.read_bytes() == b'synthetic raw bytes' for path in Path(loader.raw_path).iterdir())


def test_success_reports_presence_without_claiming_hash_verification(loader, monkeypatch, capsys):
    monkeypatch.setattr(module.requests, 'get', lambda * args, **kwargs: response())
    loader.download_data()
    assert sorted(path.name for path in Path(loader.raw_path).iterdir()) == ['BMX.xpt', 'DEMO.xpt']
    assert 'contents have not been hash-verified' in capsys.readouterr().out


def test_failed_atomic_publish_removes_temporary_files(loader, monkeypatch):
    monkeypatch.setattr(module.requests, 'get', lambda * args, **kwargs: response())
    monkeypatch.setattr(module.os, 'replace', Mock(side_effect=OSError('synthetic publish failure')))
    with pytest.raises(RuntimeError, match='Required NHANES downloads unavailable'):
        loader.download_data()
    assert list(Path(loader.raw_path).iterdir()) == []


def test_missing_demo_stops_before_dataset_processing(loader, monkeypatch):
    monkeypatch.setattr(module.pd, 'read_sas', Mock(side_effect=OSError('synthetic missing DEMO')))
    process = Mock(side_effect=AssertionError('Must not process an incomplete cycle'))
    monkeypatch.setattr(loader, '_process_dataset', process)
    with pytest.raises(RuntimeError, match='required DEMO'):
        loader.load_and_merge()
    process.assert_not_called()


def test_missing_component_stops_before_dataset_processing(loader, monkeypatch):
    monkeypatch.setattr(module.pd, 'read_sas', Mock(side_effect=[pd.DataFrame({'SEQN': [1]}), OSError('synthetic missing component')]))
    process = Mock(side_effect=AssertionError('Must not process an incomplete component set'))
    monkeypatch.setattr(loader, '_process_dataset', process)
    with pytest.raises(RuntimeError, match='required BMX'):
        loader.load_and_merge()
    process.assert_not_called()


def test_complete_required_cycles_are_merged(loader, monkeypatch):
    loader.manifest = {'a': {'DEMO': 'DEMO_A.xpt', 'BMX': 'BMX_A.xpt'},
                       'b': {'DEMO': 'DEMO_B.xpt', 'BMX': 'BMX_B.xpt'}}
    frames = {'DEMO_A.xpt': pd.DataFrame({'SEQN': [1]}), 'BMX_A.xpt': pd.DataFrame({'SEQN': [1], 'measure': [10]}),
              'DEMO_B.xpt': pd.DataFrame({'SEQN': [2]}), 'BMX_B.xpt': pd.DataFrame({'SEQN': [2], 'measure': [20]})}
    monkeypatch.setattr(module.pd, 'read_sas', lambda path: frames[Path(path).name])
    monkeypatch.setattr(loader, '_process_dataset', lambda frame: frame)
    actual = loader.load_and_merge()
    assert actual['survey_cycle'].tolist() == ['a', 'b']
    assert actual['measure'].tolist() == [10, 20]
