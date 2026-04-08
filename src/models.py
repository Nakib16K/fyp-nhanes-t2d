from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
import lightgbm as lgb

class ModelFactory:
    """
    Factory Class to instantiate Machine Learning models.
    
    This implements the Factory Design Pattern to decouple model instantiation 
    from the training pipeline. It returns unfitted estimators ready for 
    cross-validation and hyperparameter tuning.
    
    """

    @staticmethod
    def get_model(model_name: str, use_class_weight: bool = True):
        """
        Returns an unfitted scikit-learn compatible estimator.

        Args:
            model_name (str): 'lr', 'xgb', 'lgbm', or 'rf'.
            use_class_weight (bool): If True, applies algorithmic class balancing 
                                     (cost-sensitive learning). If False, assumes 
                                     SMOTE is handled externally in the pipeline.
        
        Returns:
            Estimator instance.
        """
        model_name = model_name.lower()

        # -------------------------------------------------------
        # 1. Logistic Regression (The Clinical Baseline)
        # -------------------------------------------------------
        if model_name == 'lr':
            # Uses 'liblinear' solver which is highly efficient for smaller, 
            # high-dimensional datasets and supports both L1 and L2 penalties.
            return LogisticRegression(
                class_weight='balanced' if use_class_weight else None, 
                solver='liblinear',      
                max_iter=1000,           
                random_state=42
            )
        
        # -------------------------------------------------------
        # 2. XGBoost (Extreme Gradient Boosting)
        # -------------------------------------------------------
        elif model_name == 'xgb':
            # Class weight is managed dynamically in the Optuna pipeline via 'scale_pos_weight'
            return XGBClassifier(
                eval_metric='logloss',
                random_state=42
            )

        # -------------------------------------------------------
        # 3. LightGBM (Light Gradient Boosting Machine)
        # -------------------------------------------------------
        elif model_name == 'lgbm':
            # Highly efficient tree building. verbose=-1 suppresses unnecessary C++ warnings
            return lgb.LGBMClassifier(
                class_weight='balanced' if use_class_weight else None,
                random_state=42,
                n_jobs=-1,
                verbose=-1 
            )
            
        # -------------------------------------------------------
        # 4. Random Forest
        # -------------------------------------------------------
        elif model_name == 'rf':
            # A strong bagging ensemble method, less prone to overfitting than boosting algorithms
            return RandomForestClassifier(
                class_weight='balanced' if use_class_weight else None,
                random_state=42,
                n_jobs=-1
            )

        else:
            raise ValueError(
                f"Model '{model_name}' not recognized. Valid options are: 'lr', 'xgb', 'lgbm', 'rf'."
            )