"""Build an aggregate LR reference from verified local NHANES training inputs.

Use only trusted, locally generated model artifacts. No downloads or fitting.
The output is separate from the frozen run and contains no respondent rows.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, train_test_split

from src.artifacts import load_verified_run
from src.config import CATEGORICAL_VARS, NUMERICAL_VARS, TARGET_COL
from src.data_loader import NHANESDataLoader


def checksum(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def index_hash(values):
    raw = json.dumps([int(v) for v in values], separators=(',', ':')).encode('ascii')
    return hashlib.sha256(raw).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def build(args):
    run = args.run_dir.resolve()
    output = args.output_dir.resolve()
    require(not output.exists() and not output.is_relative_to(run), 'Output must be new and outside the frozen run')
    require(checksum(run / 'f1c_manifest.json') == args.expected_run_manifest_sha256, 'Frozen manifest hash mismatch')
    require(checksum(args.raw_manifest) == args.expected_raw_manifest_sha256, 'Raw manifest hash mismatch')
    require(checksum(args.reference_report) == args.expected_reference_report_sha256, 'Reference report hash mismatch')
    reference = json.loads(args.reference_report.read_text())
    require(reference['baseline_sha256'] == args.expected_raw_manifest_sha256, 'Reference report belongs to different raw metadata')
    raw_entries = json.loads(args.raw_manifest.read_text())['data']['raw_files']
    loader = NHANESDataLoader()
    loader.raw_path = str(args.raw_dir.resolve())
    expected_names = {name for files in loader.manifest.values() for name in files.values()}
    require(len(expected_names) == 36 and expected_names == set(raw_entries), 'Unexpected raw input inventory')
    raw_hashes = {}
    for name in sorted(expected_names):
        require(Path(name).name == name, 'Unsafe raw filename')
        path = args.raw_dir / name
        require(path.is_file() and not path.is_symlink(), 'Missing or symlinked raw input')
        raw_hashes[name] = checksum(path)
        require(raw_hashes[name] == raw_entries[name]['sha256'], 'Raw input hash mismatch: ' + name)
    ready = load_verified_run(run)
    require(ready['manifest']['balancing_method'] == 'class_weight', 'Reference reconstruction requires the recorded class-weight run')
    data = loader.load_and_merge()
    require(len(data) == reference['cohort_rows'], 'Corrected cohort count mismatch')
    require(int(data[TARGET_COL].sum()) == reference['positive_labels'], 'Corrected label count mismatch')
    require(int((data['ethnicity_code'] == 7).sum()) == reference['ethnicity_7_recovered'], 'Corrected ethnicity population mismatch')
    features = [name for name in NUMERICAL_VARS + CATEGORICAL_VARS if name in data.columns]
    require(features == reference['configured_predictors'], 'Predictor inventory mismatch')
    X = data[features]
    y = data[TARGET_COL]
    outer, test, outer_y, _ = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    train, validation, train_y, _ = train_test_split(outer, outer_y, test_size=0.2, stratify=outer_y, random_state=42)
    partitions = {'train': train, 'validation': validation, 'test': test}
    splits = {}
    for name, frame in partitions.items():
        ids = data.loc[frame.index, 'respondent_id']
        splits[name] = {'rows': len(frame), 'respondent_id_order_sha256': index_hash(ids)}
        require(splits[name] == reference['split_replayed_from_seed_and_order'][name], 'Recorded split mismatch: ' + name)
        require(len(frame) == ready['manifest']['sample_counts'][name], 'Frozen run split-size mismatch')
    fold_indices, _ = next(StratifiedKFold(n_splits=10, shuffle=True, random_state=42).split(train, train_y))
    fold = train.iloc[fold_indices]
    # The verified pickle is read once. Only its existing transform is used.
    calibrated = joblib.load(ready['model_paths']['LR'])
    require(len(calibrated.calibrated_classifiers_) == 10, 'Unexpected calibration-fold inventory')
    pipeline = calibrated.calibrated_classifiers_[0].estimator
    preprocessor = pipeline.named_steps['preprocessor']
    model = pipeline.named_steps['model']
    require(np.array_equal(model.classes_, [0, 1]), 'Unexpected LR class order')
    checks = []
    for name, transformer, columns in preprocessor.column_transformer.transformers_:
        if name == 'num':
            imputer = transformer.named_steps['imputer']
            require(np.array_equal(fold[columns].to_numpy(dtype=float), imputer._fit_X, equal_nan=True), 'Fold rows/order do not match the frozen numerical fit data')
            require(int(transformer.named_steps['scaler'].n_samples_seen_) == len(fold), 'Numerical training sample count mismatch')
            checks.append('exact_numerical_fit_matrix_and_order')
        elif name in ('nom', 'ord'):
            imputer = transformer.named_steps['imputer']
            modes = fold[columns].mode().iloc[0].to_numpy(dtype=float)
            require(np.array_equal(modes, imputer.statistics_), 'Frozen categorical imputation statistics mismatch')
            if name == 'nom':
                filled = imputer.transform(fold[columns])
                encoder = transformer.named_steps['encoder']
                require(all(np.array_equal(np.unique(filled[:, i]), categories) for i, categories in enumerate(encoder.categories_)), 'Frozen category schema mismatch')
            checks.append(name + '_imputation_and_schema')
    transformed = preprocessor.transform(fold)
    names = list(transformed.columns)
    require(len(names) == model.coef_.shape[1], 'Transformed LR feature count mismatch')
    require(np.isfinite(transformed.to_numpy()).all(), 'Nonfinite transformed reference')
    mean = transformed.to_numpy(dtype=float).mean(axis=0)
    model_hash = ready['manifest']['models']['lr']['artifact']['sha256']
    background = {
        'schema': 'fyp-linear-background-v1',
        'run_id': ready['manifest']['run_id'],
        'lr_model_sha256': model_hash,
        'calibration_fold': 0,
        'reference_kind': 'calibration_fold_training_mean',
        'sample_count': len(fold),
        'feature_names': names,
        'mean': mean.tolist(),
        'provenance': {
            'raw_manifest_sha256': args.expected_raw_manifest_sha256,
            'reference_report_sha256': args.expected_reference_report_sha256,
            'raw_files_sha256': raw_hashes,
            'corrected_cohort_rows': len(data),
            'corrected_positive_labels': int(data[TARGET_COL].sum()),
            'corrected_ethnicity7_rows': int((data['ethnicity_code'] == 7).sum()),
            'split_seed': 42,
            'calibration_splits': 10,
            'partitions': splits,
            'fold_training_respondent_order_sha256': index_hash(data.loc[fold.index, 'respondent_id']),
            'frozen_preprocessing_checks': checks,
            'respondent_rows_packaged': False,
            'fit_called': False,
        },
    }
    output.mkdir(parents=True)
    target = output / 'lr_background.json'
    target.write_text(json.dumps(background, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    manifest = {
        'schema': 'fyp-local-explanations-v1',
        'run_id': ready['manifest']['run_id'],
        'frozen_manifest_sha256': args.expected_run_manifest_sha256,
        'lr_model_sha256': model_hash,
        'lr_background': {'path': target.name, 'sha256': checksum(target)},
    }
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'VERIFIED_TRAINING_REFERENCE_CREATED', 'raw_files_verified': len(raw_hashes), 'cohort_rows': len(data), 'ethnicity7_rows': background['provenance']['corrected_ethnicity7_rows'], 'calibration_fold_training_rows': len(fold), 'encoded_features': len(names), 'frozen_preprocessing_checks': checks, 'background_sha256': checksum(target), 'fit_called': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run-dir', 'raw-dir', 'raw-manifest', 'reference-report', 'output-dir'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ('expected-run-manifest-sha256', 'expected-raw-manifest-sha256', 'expected-reference-report-sha256'):
        parser.add_argument('--' + name, required=True)
    build(parser.parse_args())
