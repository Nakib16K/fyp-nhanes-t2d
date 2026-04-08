import pandas as pd
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.impute import KNNImputer, SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

# Import the variable lists from configuration
from src.config import NUMERICAL_VARS, NOMINAL_VARS, ORDINAL_VARS

class NHANESPreprocessor(BaseEstimator, TransformerMixin):
    """
    Preprocessing pipeline that handles missing data and encoding.
    
    It applies different transformations based on the data type:
    1. Numerical: KNN Imputation + Standardization (Scaling).
    2. Nominal: Mode Imputation + One-Hot Encoding.
    3. Ordinal: Mode Imputation + Identity (preserves integer codes).
    """
    
    def __init__(self, missing_threshold=0.30, knn_neighbors=5):
        self.missing_threshold = missing_threshold
        self.knn_neighbors = knn_neighbors
        self.column_transformer = None
        self.cols_to_keep = []
        self.feature_names_out = []

    def fit(self, X, y=None):
        """
        Analyzes the training data to learn missingness patterns and fitting parameters.
        """
        # 1. Missingness Gate
        # Calculate the percentage of missing values for every column.
        # Columns with missing data exceeding the threshold are dropped to reduce noise.
        missing_pct = X.isnull().mean()
        self.cols_to_keep = missing_pct[missing_pct <= self.missing_threshold].index.tolist()
        
        # Identify which of the remaining columns belong to which data type group.
        # This intersection ensures processing of only columns that passed the missingness gate.
        valid_num = [c for c in NUMERICAL_VARS if c in self.cols_to_keep]
        valid_nom = [c for c in NOMINAL_VARS if c in self.cols_to_keep]
        valid_ord = [c for c in ORDINAL_VARS if c in self.cols_to_keep]

        # 2. Define Sub-Pipelines for each data type
        
        # Numerical Pipeline: 
        # First fills missing values using K-Nearest Neighbors (captures correlations).
        # Then scales data to have Mean=0 and Variance=1 (critical for LR).
        num_pipeline = Pipeline([
            ('imputer', KNNImputer(n_neighbors=self.knn_neighbors)),
            ('scaler', StandardScaler())
        ])

        # Nominal Pipeline:
        # Fills missing values with the most frequent category.
        # Then applies One-Hot Encoding to create binary columns (e.g., Race_1, Race_2).
        # 'handle_unknown=ignore' prevents errors if new categories appear in future data.
        nom_pipeline = Pipeline([
            ('imputer', SimpleImputer(strategy='most_frequent')),
            ('encoder', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
        ])

        # Ordinal Pipeline:
        # Fills missing values with the most frequent category.
        # Does NOT encode further, preserving the integer rank (e.g., Education 1 < 5).
        ord_pipeline = Pipeline([
            ('imputer', SimpleImputer(strategy='most_frequent'))
        ])

        # 3. Create the Main ColumnTransformer
        # This combines the sub-pipelines into a single processor.
        transformers = []
        if valid_num:
            transformers.append(('num', num_pipeline, valid_num))
        if valid_nom:
            transformers.append(('nom', nom_pipeline, valid_nom))
        if valid_ord:
            transformers.append(('ord', ord_pipeline, valid_ord))

        self.column_transformer = ColumnTransformer(
            transformers=transformers,
            remainder='drop', # Explicitly drop columns not in the lists above
            verbose_feature_names_out=False
        )

        # Fit the internal transformers to the training data
        self.column_transformer.fit(X[self.cols_to_keep])
        
        return self

    def transform(self, X):
        """
        Applies the learned transformations to the data.
        Returns a Pandas DataFrame with restored column names.
        """
        # Filter the input to only include the columns kept during fit
        X_reduced = X[self.cols_to_keep]
        
        # Apply the transformations
        X_transformed = self.column_transformer.transform(X_reduced)
        
        # Recover column names from the transformers (crucial for interpretability)
        if hasattr(self.column_transformer, 'get_feature_names_out'):
            self.feature_names_out = self.column_transformer.get_feature_names_out()
        
        # Return a DataFrame instead of a numpy array
        return pd.DataFrame(X_transformed, columns=self.feature_names_out, index=X.index)

if __name__ == "__main__":
    # Test stub to verify the class works
    from src.data_loader import NHANESDataLoader
    from src.config import TARGET_COL
    
    print("Loading data for test...")
    loader = NHANESDataLoader()
    df = loader.load_and_merge()
    
    # Simulate Features (X)
    X = df.drop(columns=[TARGET_COL])
    
    print("Initializing Preprocessor...")
    preprocessor = NHANESPreprocessor(missing_threshold=0.30)
    
    print("Fitting...")
    preprocessor.fit(X)
    
    print("Transforming...")
    X_clean = preprocessor.transform(X)
    
    print(f"Clean Data Shape: {X_clean.shape}")
    print(f"Columns: {list(X_clean.columns)[:5]} ...")