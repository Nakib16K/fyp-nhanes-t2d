# ============================================================
# UNIT TESTS — ML PIPELINE COMPONENTS
# ============================================================
# Covers three components:
#   1. NHANESPreprocessor — missingness gate, output contract
#   2. Label construction — composite ground-truth logic
#   3. Sentinel-code cleaning — NHANES refused/unknown codes
#
# Run from project root:
#   pytest tests/test_pipeline.py -v
# ============================================================

import pytest
import numpy as np
import pandas as pd

from src.features import NHANESPreprocessor
from src.config import NUMERICAL_VARS, NOMINAL_VARS, ORDINAL_VARS, TARGET_COL
from src.data_loader import NHANESDataLoader


# ------------------------------------------------------------
# TEST HELPERS
# Minimal synthetic DataFrames that mimic NHANES feature structure.
# No real NHANES data is required to run these tests.
# ------------------------------------------------------------

def _make_clean_df(n=100):
    # Fully-populated feature DataFrame with no missing values
    rng = np.random.default_rng(42)
    data = {}

    # Numerical features — uniform random values
    num_cols = [c for c in NUMERICAL_VARS if c != 'waist_to_height_ratio']
    for col in num_cols:
        data[col] = rng.uniform(0, 10, size=n)

    # Engineered feature: waist-to-height ratio
    data['waist_to_height_ratio'] = rng.uniform(0.3, 0.7, size=n)

    # Nominal features — small integer codes (1 or 2)
    for col in NOMINAL_VARS:
        data[col] = rng.choice([1, 2], size=n).astype(float)

    # Ordinal features — integer codes 1 to 5
    for col in ORDINAL_VARS:
        data[col] = rng.choice([1, 2, 3, 4, 5], size=n).astype(float)

    return pd.DataFrame(data)


def _make_df_with_missing(n=100, missing_col='bmi', missing_frac=0.5):
    # DataFrame with one column at a controlled missingness level
    df = _make_clean_df(n)
    rng = np.random.default_rng(0)
    missing_rows = rng.choice(df.index, size=round(n * missing_frac), replace=False)
    df.loc[missing_rows, missing_col] = np.nan
    return df


# ------------------------------------------------------------
# TEST CLASS 1 — MISSINGNESS GATE
# Verifies that NHANESPreprocessor drops columns above the
# 30% missing threshold and retains those at or below it.
# ------------------------------------------------------------

class TestMissingnessGate:

    def test_column_above_threshold_is_dropped(self):
        # Column with 60% missingness must be excluded after fit
        df = _make_df_with_missing(missing_col='bmi', missing_frac=0.60)
        prep = NHANESPreprocessor(missing_threshold=0.30)
        prep.fit(df)
        assert 'bmi' not in prep.cols_to_keep, (
            "bmi has 60% missingness but was not removed by the missingness gate"
        )

    def test_column_below_threshold_is_kept(self):
        # Column with 10% missingness must be retained after fit
        df = _make_df_with_missing(missing_col='bmi', missing_frac=0.10)
        prep = NHANESPreprocessor(missing_threshold=0.30)
        prep.fit(df)
        assert 'bmi' in prep.cols_to_keep, (
            "bmi has only 10% missingness but was incorrectly dropped"
        )

    def test_column_at_exact_threshold_is_kept(self):
        # Gate condition is <= so a column at exactly 30% must be retained
        df = _make_df_with_missing(missing_col='bmi', missing_frac=0.30)
        prep = NHANESPreprocessor(missing_threshold=0.30)
        prep.fit(df)
        assert 'bmi' in prep.cols_to_keep, (
            "bmi at exactly 30% missingness should be kept (gate is <=)"
        )

    def test_column_just_above_threshold_is_dropped(self):
        df = _make_df_with_missing(missing_col='bmi', missing_frac=0.31)
        prep = NHANESPreprocessor(missing_threshold=0.30)
        prep.fit(df)
        assert 'bmi' not in prep.cols_to_keep


# ------------------------------------------------------------
# TEST CLASS 2 — PREPROCESSOR OUTPUT CONTRACT
# Verifies shape, type, completeness, and SHAP compatibility
# of the DataFrame returned by transform().
# ------------------------------------------------------------

class TestPreprocessorOutput:

    def test_output_is_dataframe(self):
        # transform() must return a pandas DataFrame, not a numpy array
        # SHAP requires named columns — a numpy array breaks feature attribution
        df = _make_clean_df()
        prep = NHANESPreprocessor()
        prep.fit(df)
        result = prep.transform(df)
        assert isinstance(result, pd.DataFrame), (
            "transform() returned a numpy array — SHAP requires named columns"
        )

    def test_output_has_no_missing_values(self):
        # No NaN values should remain after imputation
        df = _make_df_with_missing(missing_col='bmi', missing_frac=0.20)
        prep = NHANESPreprocessor()
        prep.fit(df)
        result = prep.transform(df)
        assert result.isnull().sum().sum() == 0, (
            "Transformed output still contains NaN values after imputation"
        )

    def test_output_row_count_matches_input(self):
        # transform() must not drop rows — count must equal input
        df = _make_clean_df(n=80)
        prep = NHANESPreprocessor()
        prep.fit(df)
        result = prep.transform(df)
        assert len(result) == 80, (
            f"Expected 80 rows after transform, got {len(result)}"
        )

    def test_output_columns_are_named_strings(self):
        # All column names must be strings — integer indices break SHAP
        df = _make_clean_df()
        prep = NHANESPreprocessor()
        prep.fit(df)
        result = prep.transform(df)
        for col in result.columns:
            assert isinstance(col, str), (
                f"Column '{col}' is not a string — will break SHAP feature naming"
            )

    def test_unseen_categories_do_not_raise(self):
        # Nominal features with unseen categories at inference must not raise.
        # handle_unknown='ignore' produces all-zero rows for unknown categories.
        df_train = _make_clean_df(n=100)
        prep = NHANESPreprocessor()
        prep.fit(df_train)

        df_test = _make_clean_df(n=10)
        # Inject an unseen category value (99) into a nominal column
        df_test.loc[0, NOMINAL_VARS[0]] = 99.0

        try:
            result = prep.transform(df_test)
            assert len(result) == 10
        except Exception as e:
            pytest.fail(
                f"transform() raised an exception on unseen category: {e}"
            )


# ------------------------------------------------------------
# TEST CLASS 3 — LABEL CONSTRUCTION
# Exercises the actual composite label construction in
# data_loader._process_dataset:
#   diabetic  = HbA1c >= 6.5  OR  insulin == 1  OR  pills == 1
#   healthy   = HbA1c <  6.5  AND insulin != 1  AND pills != 1
#   ambiguous = missing HbA1c AND no medication data -> dropped
# ------------------------------------------------------------

class TestLabelConstruction:

    def _apply_label_logic(self, hba1c, insulin, pills):
        df = pd.DataFrame({
            'RIDAGEYR': np.full(len(hba1c), 45),
            'LBXGH': hba1c,
            'DIQ050': insulin,
            'DIQ070': pills,
        })
        return NHANESDataLoader()._process_dataset(df)[TARGET_COL].to_numpy()

    def test_high_hba1c_alone_gives_label_1(self):
        label = self._apply_label_logic(
            hba1c=np.array([7.0]), insulin=np.array([0]), pills=np.array([0])
        )
        assert label[0] == 1

    def test_insulin_alone_gives_label_1(self):
        label = self._apply_label_logic(
            hba1c=np.array([5.0]), insulin=np.array([1]), pills=np.array([0])
        )
        assert label[0] == 1

    def test_pills_alone_gives_label_1(self):
        label = self._apply_label_logic(
            hba1c=np.array([5.0]), insulin=np.array([0]), pills=np.array([1])
        )
        assert label[0] == 1

    def test_all_negative_gives_label_0(self):
        label = self._apply_label_logic(
            hba1c=np.array([5.0]), insulin=np.array([0]), pills=np.array([0])
        )
        assert label[0] == 0

    def test_boundary_hba1c_6_5_gives_label_1(self):
        # Exact boundary: HbA1c = 6.5 must produce label 1 (>= condition)
        label = self._apply_label_logic(
            hba1c=np.array([6.5]), insulin=np.array([0]), pills=np.array([0])
        )
        assert label[0] == 1

    def test_just_below_boundary_hba1c_gives_label_0(self):
        # HbA1c = 6.49 with no medication must produce label 0
        label = self._apply_label_logic(
            hba1c=np.array([6.49]), insulin=np.array([0]), pills=np.array([0])
        )
        assert label[0] == 0

    def test_missing_hba1c_without_medication_is_unlabelled(self):
        label = self._apply_label_logic(
            hba1c=np.array([np.nan]), insulin=np.array([0]), pills=np.array([0])
        )
        assert len(label) == 0

    def test_medication_defines_label_when_hba1c_is_missing(self):
        label = self._apply_label_logic(
            hba1c=np.array([np.nan]), insulin=np.array([1]), pills=np.array([0])
        )
        assert label[0] == 1


# ------------------------------------------------------------
# TEST CLASS 4 — SENTINEL-CODE CLEANING
# Exercises the actual variable-specific response rules.
# Valid ethnicity and alcohol quantity codes must survive;
# numerical columns are not response-code cleaned.
# ------------------------------------------------------------

class TestSpecialCodeCleaning:

    def _apply_sentinel_cleaning(self, df):
        return NHANESDataLoader()._clean_special_codes(df.copy())

    def test_yes_no_nonresponse_7_replaced_with_nan(self):
        df = pd.DataFrame({'family_history_diabetes': [1.0, 7.0, 2.0]})
        result = self._apply_sentinel_cleaning(df)
        assert pd.isna(result['family_history_diabetes'].iloc[1]), (
            "A yes/no nonresponse code was not replaced with NaN"
        )

    def test_sentinel_99_replaced_with_nan(self):
        df = pd.DataFrame({ORDINAL_VARS[0]: [1.0, 99.0, 3.0]})
        result = self._apply_sentinel_cleaning(df)
        assert pd.isna(result[ORDINAL_VARS[0]].iloc[1]), (
            "Sentinel value 99 was not replaced with NaN"
        )

    def test_valid_values_are_not_affected(self):
        df = pd.DataFrame({NOMINAL_VARS[0]: [1.0, 2.0, 1.0]})
        result = self._apply_sentinel_cleaning(df)
        assert list(result[NOMINAL_VARS[0]]) == [1.0, 2.0, 1.0], (
            "Valid values were incorrectly altered by sentinel cleaning"
        )

    def test_numerical_columns_are_not_cleaned(self):
        # Cleaning must not touch numerical columns — 7.0 is a valid age
        df = pd.DataFrame({
            'family_history_diabetes': [1.0, 7.0, 2.0],
            'age_years': [25.0, 7.0, 45.0]
        })
        result = self._apply_sentinel_cleaning(df)
        assert result['age_years'].iloc[1] == 7.0, (
            "Sentinel cleaning incorrectly altered a numerical column (age_years)"
        )

    def test_valid_ethnicity_code_7_is_preserved(self):
        df = pd.DataFrame({'ethnicity_code': [1.0, 7.0, 6.0]})
        result = self._apply_sentinel_cleaning(df)
        assert result['ethnicity_code'].tolist() == [1.0, 7.0, 6.0]

    def test_unused_ethnicity_code_5_is_rejected(self):
        with pytest.raises(ValueError, match='Invalid RIDRETH3'):
            self._apply_sentinel_cleaning(pd.DataFrame({'ethnicity_code': [5.0]}))

    def test_alcohol_quantity_codes_are_not_yes_no_nonresponses(self):
        df = pd.DataFrame({'alcohol_frequency': [7.0, 9.0, 777.0, 999.0]})
        result = self._apply_sentinel_cleaning(df)
        assert result['alcohol_frequency'].iloc[:2].tolist() == [7.0, 9.0]
        assert result['alcohol_frequency'].iloc[2:].isna().all()
