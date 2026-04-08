import os
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
        print(f"Checking data integrity in {self.raw_path}...")
        
        for cycle, files in self.manifest.items():
            base_url = BASE_URLS[cycle]
            for component, filename in files.items():
                file_path = os.path.join(self.raw_path, filename)
                
                if not os.path.exists(file_path):
                    url = f"{base_url}/{filename}"
                    print(f"Downloading missing file: {filename} from {url}")
                    
                    try:
                        # Simple download using the configured URLs
                        response = requests.get(url, timeout=30)
                        response.raise_for_status()
                        
                        with open(file_path, 'wb') as f:
                            f.write(response.content)
                            print(" - Download complete.")
                            
                    except Exception as e:
                        print(f" [ERROR] Failed to download {filename}: {e}")

        print("Data integrity check passed. All files present.")

    def load_and_merge(self) -> pd.DataFrame:
        master_df = pd.DataFrame()
        
        for cycle, files in self.manifest.items():
            print(f"Processing Cycle: {cycle}...")
            
            # 1. Load DEMO first (Base)
            demo_path = os.path.join(self.raw_path, files["DEMO"])
            try:
                cycle_df = pd.read_sas(demo_path)
            except Exception as e:
                print(f"Critical Error loading DEMO for {cycle}: {e}")
                continue
                
            # 2. Merge other components
            for component, filename in files.items():
                if component == "DEMO": continue
                
                file_path = os.path.join(self.raw_path, filename)
                try:
                    comp_df = pd.read_sas(file_path)
                    # Merge on SEQN (Respondent ID)
                    cycle_df = pd.merge(cycle_df, comp_df, on='SEQN', how='left')
                except Exception as e:
                    print(f"Warning: Could not merge {component} ({filename}): {e}")
            
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
        """
        Replaces NHANES 'Refused' (7, 77, 777) and 'Don't Know' (9, 99, 999) 
        codes with NaN so they are handled by the Imputer rather than treated as real values.
        """
        # NHANES standard missing codes often depend on field length, 
        # but 7/9/77/99 are the most common for categorical vars.
        missing_codes = [7, 9, 77, 99, 777, 999]
        
        # Only apply to Categorical variables (Nominal + Ordinal)
        # Checks intersection with columns actually present in df
        target_cols = [c for c in (NOMINAL_VARS + ORDINAL_VARS) if c in df.columns]
        
        for col in target_cols:
            # Replace the codes with NaN
            df[col] = df[col].replace(missing_codes, np.nan)
            
        print(f"Cleaned special codes (Refused/Don't Know) in {len(target_cols)} categorical columns.")
        return df

if __name__ == "__main__":
    loader = NHANESDataLoader()
    loader.download_data()
    df = loader.load_and_merge()
    print(df.head())