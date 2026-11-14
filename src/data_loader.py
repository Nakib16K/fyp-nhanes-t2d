import os
import tempfile
import pandas as pd
import numpy as np
import requests
from typing import Dict, List, Optional

from src.config import (
    RAW_DATA_PATH,
    NHANES_FILE_MANIFEST,
    BASE_URLS,
    TARGET_SOURCE_COLS,
    ID_COLS,
    FEATURE_MAPPING,
    TARGET_COL,
    NOMINAL_VARS,
    ORDINAL_VARS
)

class NHANESDataLoader:
    
    def __init__(self):
        self.raw_path = RAW_DATA_PATH
        self.manifest = NHANES_FILE_MANIFEST
        
    def download_data(self):
        print(f"Checking required raw files in {self.raw_path}...")
        failures = []
        for cycle, files in self.manifest.items():
            base_url = BASE_URLS[cycle]
            for component, filename in files.items():
                file_path = os.path.join(self.raw_path, filename)
                if os.path.isfile(file_path) and os.path.getsize(file_path) > 0:
                    continue
                url = f"{base_url}/{filename}"
                print(f"Downloading missing or empty file: {filename} from {url}")
                pending_path = None
                try:
                    response = requests.get(url, timeout=30)
                    response.raise_for_status()
                    if not response.content:
                        raise ValueError("Downloaded file is empty")
                    # Publish only a complete download, never a partial final file.
                    with tempfile.NamedTemporaryFile(
                        mode='wb', dir=self.raw_path, prefix=f".{filename}.",
                        suffix='.part', delete=False,
                    ) as pending:
                        pending_path = pending.name
                        pending.write(response.content)
                    os.replace(pending_path, file_path)
                    print(" - Download complete.")
                except Exception as error:
                    if pending_path and os.path.isfile(pending_path):
                        os.remove(pending_path)
                    failures.append(f"{cycle}/{filename}")
                    print(f" [ERROR] Failed to download {filename}: {error}")
        if failures:
            raise RuntimeError("Required NHANES downloads unavailable: " + ", ".join(failures))
        print("Required raw files are present and non-empty; contents have not been hash-verified.")

    def load_and_merge(self) -> pd.DataFrame:
        master_df = pd.DataFrame()
        
        for cycle, files in self.manifest.items():
            print(f"Processing Cycle: {cycle}...")
            
            # 1. Load DEMO first (Base)
            demo_path = os.path.join(self.raw_path, files["DEMO"])
            try:
                cycle_df = pd.read_sas(demo_path)
            except Exception as e:
                raise RuntimeError(f"Could not load required DEMO file {files['DEMO']} for {cycle}") from e
                
            # 2. Merge other components
            for component, filename in files.items():
                if component == "DEMO": continue
                
                file_path = os.path.join(self.raw_path, filename)
                try:
                    comp_df = pd.read_sas(file_path)
                    # Merge on SEQN (Respondent ID)
                    cycle_df = pd.merge(cycle_df, comp_df, on='SEQN', how='left')
                except Exception as e:
                    raise RuntimeError(f"Could not load or merge required {component} file {filename} for {cycle}") from e
            
            cycle_df['survey_cycle'] = cycle
            master_df = pd.concat([master_df, cycle_df], ignore_index=True)
            
        print(f"Raw merged shape: {master_df.shape}")
        return self._process_dataset(master_df)

    def _process_dataset(self, df: pd.DataFrame) -> pd.DataFrame:
        rename_map = {**ID_COLS, **TARGET_SOURCE_COLS, **FEATURE_MAPPING}
        df = df.rename(columns=rename_map)

        initial_count = len(df)
        df = df[df['age_years'] >= 20].copy()
        print(f"Dropped {initial_count - len(df)} rows (Age < 20).")

        # --- FEATURE ENGINEERING ---
        # Calculate Waist-to-Height Ratio
        # Pandas handles missing values (NaN) automatically during division
        if 'waist_circumference' in df.columns and 'height_cm' in df.columns:
            df['waist_to_height_ratio'] = df['waist_circumference'] / df['height_cm']

        # Ground Truth Logic
        has_high_a1c = df['hba1c_percent'] >= 6.5
        on_insulin = df['taking_insulin'] == 1
        on_pills = df['taking_diabetes_pills'] == 1
        
        is_diabetic = has_high_a1c | on_insulin | on_pills
        is_healthy = (df['hba1c_percent'] < 6.5) & (~on_insulin) & (~on_pills)

        df[TARGET_COL] = np.nan
        df.loc[is_diabetic, TARGET_COL] = 1
        df.loc[is_healthy, TARGET_COL] = 0

        df = df.dropna(subset=[TARGET_COL])
        print(f"Final labeled count: {len(df)} (Diabetic: {df[TARGET_COL].sum()})")
        
        # Apply Clean-up for Refused/Don't Know codes
        df = self._clean_special_codes(df)

        # Columns to keep logic (ADDED waist_to_height_ratio here so it survives)
        all_cols_needed = list(FEATURE_MAPPING.values()) + ['survey_cycle', TARGET_COL, 'waist_to_height_ratio'] + list(ID_COLS.values())
        
        existing_cols = [c for c in all_cols_needed if c in df.columns]
        
        print(f"Features retained: {len(existing_cols)}")
        
        return df[existing_cols]

    def _clean_special_codes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Field-specific missing response handling, never erase RIDRETH3=7.

        `alcohol_frequency` remains in the private processed audit data, but is
        NOT used as a predictor. ALQ120Q is a quantity needing its separate
        ALQ120U unit; the 2017-2018 cycle instead uses ALQ121. Do not imply
        that its unharmonised values represent days/year.
        """
        response_codes = {
            "gender_code": (),
            "ethnicity_code": (),  # RIDRETH3=7 is Other Race / Multiracial.
            "history_high_bp": (7, 9, 77, 99, 777, 999),
            "smoked_100_cigs": (7, 9, 77, 99, 777, 999),
            "family_history_diabetes": (7, 9, 77, 99, 777, 999),
            "vigorous_activity": (7, 9, 77, 99, 777, 999),
            "education_level": (7, 9, 77, 99, 777, 999),
            "alcohol_frequency": (777, 999),  # 7 and 9 are valid quantities.
        }
        expected = set(NOMINAL_VARS + ORDINAL_VARS + ["alcohol_frequency"])
        if not expected.issubset(response_codes):
            raise ValueError("No variable-specific cleaning rule for a configured feature")
        for name, codes in response_codes.items():
            if name in df.columns and codes:
                df[name] = df[name].replace(list(codes), np.nan)
        if "ethnicity_code" in df.columns:
            invalid = df["ethnicity_code"].dropna()
            invalid = invalid[~invalid.isin((1, 2, 3, 4, 6, 7))]
            if not invalid.empty:
                raise ValueError("Invalid RIDRETH3 code in raw NHANES data")
        return df
if __name__ == "__main__":
    loader = NHANESDataLoader()
    loader.download_data()
    df = loader.load_and_merge()
    print(df.head())