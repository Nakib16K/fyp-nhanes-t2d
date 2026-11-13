import os
import json
import joblib
import pandas as pd
import numpy as np
import warnings
import optuna

# Suppress sklearn deprecation warnings about penalty parameter
warnings.filterwarnings('ignore', category=FutureWarning, module='sklearn')
warnings.filterwarnings('ignore', category=UserWarning, module='sklearn.linear_model')
# Suppress Optuna logging to keep console output clean; only show warnings/errors
optuna.logging.set_verbosity(optuna.logging.WARNING)

# Set Matplotlib to Non-Interactive 'Agg' Backend to prevent threading crashes
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import seaborn as sns

import shap  
from datetime import datetime

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import (
    classification_report, roc_auc_score, confusion_matrix, 
    roc_curve, precision_recall_curve, average_precision_score,
    accuracy_score, f1_score, precision_score, recall_score
)
from sklearn.calibration import CalibratedClassifierCV
from imblearn.pipeline import Pipeline as ImbPipeline
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import RandomUnderSampler # Added for Undersampling Mode

from src.config import (
    TARGET_COL, 
    CATEGORICAL_VARS, 
    NUMERICAL_VARS,
    MODELS_DIR, 
    PROCESSED_DATA_PATH,
    REPORTS_DIR
)
from src.data_loader import NHANESDataLoader
from src.features import NHANESPreprocessor
from src.models import ModelFactory
from src.data_dictionary import generate_data_dictionary
from src.validation_protocol import (
    choose_validation_threshold, classify_at_threshold, subgroup_fairness,
)
from src.artifacts import write_manifest


class ModelTrainer:
    """
    The Orchestrator Class.
    Manages data ingestion, preprocessing, Bayesian hyperparameter tuning (Optuna), 
    comprehensive metric reporting, and algorithmic fairness evaluation.
    """
    
    def __init__(self):
        self.loader = NHANESDataLoader()
        
        # Tracking dictionaries to store artifacts for ALL models (FastAPI requirement)
        self.fitted_models = {}
        self.raw_pipelines = {}
        # Thresholds selected on validation data, never the final holdout.
        self.selected_thresholds = {}
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
        self.run_dir = os.path.join(REPORTS_DIR, "results", f"run_{timestamp}")
        os.makedirs(self.run_dir, exist_ok=True)
        print(f">>> Reporting initialized at: {self.run_dir}")
        
    def run(self, balancing_method='class_weight', use_cached_params=True):
        print(f">>> 1. DATA INGESTION (Balancing Strategy: {balancing_method.upper()})")
        self.loader.download_data()
        df = self.loader.load_and_merge()
        
        selected_features = NUMERICAL_VARS + CATEGORICAL_VARS
        available_features = [f for f in selected_features if f in df.columns]
        print(f"Selected {len(available_features)} non-invasive domain features.")
        
        X = df[available_features].copy()
        y = df[TARGET_COL].copy()
        
        master_path = os.path.join(PROCESSED_DATA_PATH, "master_dataset.csv")
        df.to_csv(master_path, index=False)

        dict_path = os.path.join(self.run_dir, "data_dictionary_master_dataset.csv")
        generate_data_dictionary(master_path, dict_path)
        print(f">>> Data dictionary saved: {dict_path}")

        # Retain the exact original 20% stratified holdout selection.
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, stratify=y, random_state=42
        )
        # Carve an independent 20% validation partition from the remaining 80%.
        # 64% training, 16% validation, 20% retained final test overall.
        # The test partition was reused in earlier experiments; it is not a new holdout.
        X_fit, X_validation, y_fit, y_validation = train_test_split(
            X_train, y_train, test_size=0.2, stratify=y_train, random_state=42
        )
        print(f"Dataset split: training={len(X_fit)}, validation={len(X_validation)}, test={len(X_test)}")

        print("\n>>> 2. MODEL TRAINING & TUNING")
        use_class_weight = (balancing_method == 'class_weight')
        cv_split = StratifiedKFold(n_splits=10, shuffle=True, random_state=42)
        
        results_summary = []
        models_to_train = ['lr', 'rf', 'lgbm', 'xgb'] 
        
        for model_name in models_to_train:
            print(f"\n--- Processing {model_name.upper()} ---")
            
            # -----------------------------------------------------------
            # BAYESIAN OPTIMIZATION OBJECTIVE FUNCTION
            # -----------------------------------------------------------
            def objective(trial):
                # 1. Define hyperparameters dynamically based on the model
                params = {}
                if model_name == 'lr':
                    params['C'] = trial.suggest_float('C', 1e-4, 100, log=True)
                    params['penalty'] = trial.suggest_categorical('penalty', ['l1', 'l2'])
                elif model_name == 'xgb':
                    params['max_depth'] = trial.suggest_int('max_depth', 3, 8)
                    params['min_child_weight'] = trial.suggest_int('min_child_weight', 1, 6)
                    params['learning_rate'] = trial.suggest_float('learning_rate', 0.01, 0.2, log=True)
                    params['n_estimators'] = trial.suggest_int('n_estimators', 100, 400)
                    params['subsample'] = trial.suggest_float('subsample', 0.5, 1.0)
                    params['colsample_bytree'] = trial.suggest_float('colsample_bytree', 0.5, 1.0)
                    if use_class_weight:
                        params['scale_pos_weight'] = trial.suggest_float('scale_pos_weight', 1, 50, log=True)
                elif model_name == 'lgbm':
                    params['num_leaves'] = trial.suggest_int('num_leaves', 20, 150)
                    params['max_depth'] = trial.suggest_int('max_depth', 3, 10)
                    params['learning_rate'] = trial.suggest_float('learning_rate', 0.01, 0.2, log=True)
                    params['n_estimators'] = trial.suggest_int('n_estimators', 100, 400)
                    params['subsample'] = trial.suggest_float('subsample', 0.5, 1.0)
                    params['min_child_samples'] = trial.suggest_int('min_child_samples', 10, 50)
                elif model_name == 'rf':
                    params['n_estimators'] = trial.suggest_int('n_estimators', 100, 500)
                    params['max_depth'] = trial.suggest_int('max_depth', 5, 20)
                    params['min_samples_split'] = trial.suggest_int('min_samples_split', 2, 20)
                    params['min_samples_leaf'] = trial.suggest_int('min_samples_leaf', 1, 10)

                # 2. Build Pipeline
                steps = [('preprocessor', NHANESPreprocessor(missing_threshold=0.30))]
                
                # Check balancing mode and append the correct imblearn technique
                if balancing_method == 'smote':
                    steps.append(('smote', SMOTE(random_state=42)))
                elif balancing_method == 'undersample':
                    steps.append(('undersample', RandomUnderSampler(random_state=42)))
                
                model = ModelFactory.get_model(model_name, use_class_weight=use_class_weight)
                model.set_params(**params)
                steps.append(('model', model))
                
                pipeline = ImbPipeline(steps)
                
                # 3. Evaluate using Stratified 10-Fold CV (Optimizing for ROC-AUC)
                score = cross_val_score(pipeline, X_fit, y_fit, cv=cv_split, scoring='roc_auc', n_jobs=-1)
                return score.mean()

            # -----------------------------------------------------------
            # CACHING LOGIC & OPTIMIZATION EXECUTION
            # -----------------------------------------------------------
            cache_path = os.path.join(MODELS_DIR, f"best_params_{model_name}_{balancing_method}_f1b_train64_seed42.json")
            best_params = None
            
            if use_cached_params and os.path.exists(cache_path):
                print(f"Found cached best params for {model_name.upper()}. Loading from file...")
                with open(cache_path, 'r') as f:
                    cache_data = json.load(f)
                    best_params = cache_data.get('params', {})
            else:
                print(f"Running Optuna Bayesian Optimization for {model_name.upper()}...")
                study = optuna.create_study(direction='maximize', sampler=optuna.samplers.TPESampler(seed=42))
                study.optimize(objective, n_trials=50)
                
                best_params = study.best_params
                best_cv_auc = study.best_value
                
                print(f"Best Optuna Params: {best_params}")
                print(f"Best CV AUC: {best_cv_auc:.4f}")
                
                # Save best params to cache
                cache_data = {
                    "model": model_name,
                    "balancing": balancing_method,
                    "params": best_params,
                    "best_cv_auc": best_cv_auc
                }
                with open(cache_path, 'w') as f:
                    json.dump(cache_data, f, indent=4)
                print(f"Saved best params to {cache_path}")
            
            # -----------------------------------------------------------
            # FINAL MODEL TRAINING & CALIBRATION
            # -----------------------------------------------------------
            final_steps = [('preprocessor', NHANESPreprocessor(missing_threshold=0.30))]
            
            # Check balancing mode for final pipeline
            if balancing_method == 'smote':
                final_steps.append(('smote', SMOTE(random_state=42)))
            elif balancing_method == 'undersample':
                final_steps.append(('undersample', RandomUnderSampler(random_state=42)))
            
            best_model_instance = ModelFactory.get_model(model_name, use_class_weight=use_class_weight)
            best_model_instance.set_params(**best_params)
            final_steps.append(('model', best_model_instance))
            
            best_est = ImbPipeline(final_steps)
            best_est.fit(X_fit, y_fit)
            
            print("Calibrating probabilities...")
            calibrated_model = CalibratedClassifierCV(best_est, cv=cv_split, method='isotonic')
            calibrated_model.fit(X_fit, y_fit)
            
            # -----------------------------------------------------------
            # PREDICTION & EVALUATION
            # -----------------------------------------------------------
            # Select the operating threshold exclusively from the validation set.
            validation_proba = calibrated_model.predict_proba(X_validation)[:, 1]
            threshold_choice = choose_validation_threshold(y_validation, validation_proba)
            self.selected_thresholds[model_name] = threshold_choice
            best_thresh = threshold_choice.threshold

            # Evaluate the frozen decision rule on the retained test partition.
            # Earlier reuse of this partition limits independent performance claims.
            y_proba = calibrated_model.predict_proba(X_test)[:, 1]
            y_pred = classify_at_threshold(y_proba, best_thresh)
            best_f1 = f1_score(y_test, y_pred, zero_division=0)
            
            # Calculate expanded metrics
            auc = roc_auc_score(y_test, y_proba)
            pr_auc = average_precision_score(y_test, y_proba) 
            acc = accuracy_score(y_test, y_pred)
            prec = precision_score(y_test, y_pred)
            rec = recall_score(y_test, y_pred)
            
            cm = confusion_matrix(y_test, y_pred)
            tn, fp, fn, tp = cm.ravel()
            sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0 
            specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
            
            print(f"Test AUC: {auc:.4f} | PR-AUC: {pr_auc:.4f} | F1: {best_f1:.4f}")
            
            self._save_artifacts(model_name, calibrated_model, y_test, y_pred, y_proba, best_thresh, pr_auc, raw_pipeline=best_est)
            
            results_summary.append({
                "Model": model_name.upper(),
                "Balancing": balancing_method,
                "AUC": auc,
                "PR_AUC": pr_auc,
                "F1_Score": best_f1,
                "Accuracy": acc,
                "Precision": prec,
                "Recall_Sensitivity": sensitivity,
                "Specificity": specificity,
                "Best_Threshold": best_thresh,
                "Threshold_Source": "validation",
                "Validation_F1": threshold_choice.validation_f1,
                "Best_Params": str(best_params)
            })
            
            # -----------------------------------------------------------
            # FULL PERSISTENCE (FastAPI Requirement)
            # -----------------------------------------------------------
            # Persist each model under its own run, never in shared models/.
            run_models_dir = os.path.join(self.run_dir, "models")
            os.makedirs(run_models_dir, exist_ok=True)
            model_path = os.path.join(run_models_dir, f"{model_name}_pipeline.pkl")
            joblib.dump(calibrated_model, model_path)
            print(f"-> Run-specific model saved to {model_path}")
            
            self.fitted_models[model_name] = calibrated_model
            self.raw_pipelines[model_name] = best_est

        # -----------------------------------------------------------
        # POST-TRAINING TASKS (SHAP & Fairness)
        # -----------------------------------------------------------
        for model_name in ['lr', 'xgb', 'lgbm', 'rf']:
            if model_name in self.raw_pipelines:
                print(f"\n>>> 3. GENERATING SHAP EXPLANATIONS ({model_name.upper()})")
                try:
                    self._generate_shap(self.raw_pipelines[model_name], X_fit, X_test, model_name)
                except Exception as e:
                    print(f"Could not generate SHAP plots for {model_name}: {e}")
        
        print("\n>>> 4. GENERATING ALGORITHMIC FAIRNESS REPORT")
        self._generate_fairness_report(X_test, y_test)
        
        pd.DataFrame(results_summary).to_csv(os.path.join(self.run_dir, "summary_metrics.csv"), index=False)
        # Publish the completed-run marker only after models, metrics,
        # global SHAP, interpretations, and fairness artifacts all exist.
        write_manifest(
            self.run_dir, balancing_method, self.selected_thresholds,
            {"train": len(X_fit), "validation": len(X_validation), "test": len(X_test)},
        )
        print(f"\n>>> Verified run complete: {self.run_dir}")


    @staticmethod
    def _build_shap_label_map(run_dir):
        """Build a complete readable name map for ALL features (numerical + categorical)."""
        import csv as _csv, json as _json

        # Standardised readable names for numerical and ordinal features
        # (these have no encoding suffix so must be hardcoded)
        NUMERICAL_NAMES = {
            "age_years":              "Age (years)",
            "bmi":                    "BMI",
            "waist_circumference":    "Waist Circumference (cm)",
            "waist_to_height_ratio":  "Waist-to-Height Ratio",
            "systolic_bp":            "Systolic BP (mmHg)",
            "diastolic_bp":           "Diastolic BP (mmHg)",
            "pulse_60s":              "Resting Pulse (bpm)",
            "poverty_ratio":          "Poverty Ratio",
            "education_level":        "Education Level",
            "alcohol_frequency":      "Alcohol Frequency (days/year)",
        }

        # Categorical label corrections (override auto-generated ones)
        CATEGORICAL_OVERRIDES = {
            "history_high_bp": "High BP History",
            "smoked_100_cigs": "Smoked 100+ Cigarettes",
            "family_history_diabetes": "Family Diabetes History",
            "vigorous_activity": "Vigorous Activity",
            "gender_code": "Gender",
            "ethnicity_code": "Ethnicity",
        }

        label_map = dict(NUMERICAL_NAMES)

        dd_path = os.path.join(run_dir, "data_dictionary_master_dataset.csv")
        if not os.path.exists(dd_path):
            return label_map
        try:
            with open(dd_path) as f:
                reader = _csv.DictReader(f)
                for row in reader:
                    col = row["column"]
                    cats_raw = row.get("categories_json", "").strip()
                    if cats_raw:
                        cats = _json.loads(cats_raw)
                        for cat in cats:
                            code = cat["code"]
                            meaning = cat.get("meaning", "")
                            if meaning:
                                # Use override prefix if defined, else auto-generate
                                prefix = CATEGORICAL_OVERRIDES.get(
                                    col,
                                    col.replace("_code", "").replace("_", " ").title()
                                )
                                readable = f"{prefix}: {meaning}"
                                label_map[f"{col}_{float(code)}"] = readable
                                if float(code) == int(float(code)):
                                    label_map[f"{col}_{int(float(code))}"] = readable
        except Exception as e:
            print(f"Warning: could not load SHAP label map: {e}")
        return label_map

    @staticmethod
    def _apply_shap_labels(feature_names, label_map):
        return [label_map.get(n, n) for n in feature_names]

    def _generate_shap(self, pipeline, X_train, X_test, model_name):
        try:
            preprocessor = pipeline.named_steps['preprocessor']
            model = pipeline.named_steps['model']

            X_train_trans = preprocessor.transform(X_train)
            X_test_trans = preprocessor.transform(X_test)

            # Apply readable feature names from data dictionary
            label_map = self._build_shap_label_map(self.run_dir)
            readable = self._apply_shap_labels(list(X_test_trans.columns), label_map)
            X_test_plot = X_test_trans.copy()
            X_test_plot.columns = readable

            if model_name == 'lr':
                # LinearExplainer: use encoded data for computation, readable for display
                explainer = shap.LinearExplainer(model, X_train_trans)
                shap_values = explainer.shap_values(X_test_trans)
            else:
                # TreeExplainer: MUST use encoded data (raw column names)
                # Passing readable names causes XGBoost to silently return
                # background values instead of per-sample SHAP values.
                explainer = shap.TreeExplainer(model)
                shap_values = explainer.shap_values(X_test_trans)
                # Safeguard: Resolve varying outputs from RF/XGB
                if isinstance(shap_values, list):
                    shap_values = shap_values[1]
                elif len(np.array(shap_values).shape) == 3:
                    shap_values = np.array(shap_values)[:, :, 1]

            plt.figure(figsize=(10, 6))
            # Use X_test_plot (with readable names) only for the DISPLAY in summary_plot
            shap.summary_plot(shap_values, X_test_plot, show=False)
            plt.title(f"SHAP Feature Importance - {model_name.upper()}", fontsize=16)
            plt.tight_layout()
            plt.savefig(os.path.join(self.run_dir, f"{model_name}_shap_summary.png"))
            plt.close()
            print(f"SHAP Summary plot saved for {model_name}.")
        except Exception as e:
            print(f"SHAP generation failed: {e}")
            raise e

    def _generate_fairness_report(self, X_test, y_test):
        """Audit the holdout with the already-selected validation threshold.

        This audit does not retune any threshold on test labels. Missing subgroup
        values are reported explicitly; rates with zero denominators are blank.
        """
        target_model = 'xgb' if 'xgb' in self.fitted_models else 'lr'
        model = self.fitted_models[target_model]
        selection = self.selected_thresholds.get(target_model)
        if selection is None or selection.selected_from != 'validation':
            raise RuntimeError("Missing frozen validation threshold for fairness model")

        y_proba = model.predict_proba(X_test)[:, 1]
        fairness_results = []
        for attribute, column in [('Gender', 'gender_code'), ('Ethnicity', 'ethnicity_code')]:
            if column not in X_test.columns:
                continue
            for group in subgroup_fairness(
                y_test, y_proba, X_test[column].to_numpy(), selection
            ):
                fairness_results.append({
                    'Attribute': attribute,
                    'Group': group['group'],
                    'FNR (Miss Rate)': group['false_negative_rate'],
                    'FPR (False Alarm Rate)': group['false_positive_rate'],
                    'Support': group['support'],
                    'Actual_Positive': group['actual_positive'],
                    'Actual_Negative': group['actual_negative'],
                    'Threshold': selection.threshold,
                    'Threshold_Source': selection.selected_from,
                    'Model': target_model.upper(),
                })

        if fairness_results:
            pd.DataFrame(fairness_results).to_csv(
                os.path.join(self.run_dir, "algorithmic_fairness_report.csv"), index=False
            )
            print("Fairness report saved with frozen threshold and group counts.")

    def _save_artifacts(self, model_name, pipeline, y_test, y_pred, y_proba, threshold, pr_auc, raw_pipeline=None):
        report = classification_report(y_test, y_pred, output_dict=True)
        pd.DataFrame(report).transpose().to_csv(os.path.join(self.run_dir, f"{model_name}_report.csv"))
        
        plt.figure(figsize=(6, 5))
        cm = confusion_matrix(y_test, y_pred)
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=False)
        plt.title(f"Confusion Matrix: {model_name.upper()}")
        plt.savefig(os.path.join(self.run_dir, f"{model_name}_confusion_matrix.png"))
        plt.close()
        
        plt.figure(figsize=(6, 5))
        fpr, tpr, _ = roc_curve(y_test, y_proba)
        plt.plot(fpr, tpr, label=f"AUC = {roc_auc_score(y_test, y_proba):.3f}")
        plt.plot([0, 1], [0, 1], 'k--')
        plt.title(f"ROC Curve: {model_name.upper()}")
        plt.legend()
        plt.savefig(os.path.join(self.run_dir, f"{model_name}_roc_curve.png"))
        plt.close()

        plt.figure(figsize=(6, 5))
        prec, rec, _ = precision_recall_curve(y_test, y_proba)
        plt.plot(rec, prec, label=f"PR-AUC = {pr_auc:.3f}")
        plt.xlabel("Recall")
        plt.ylabel("Precision")
        plt.title(f"PR Curve: {model_name.upper()}")
        plt.legend()
        plt.savefig(os.path.join(self.run_dir, f"{model_name}_pr_curve.png"))
        plt.close()

        self._write_interpretation(model_name, y_test, y_pred, y_proba, threshold, pr_auc)

    def _write_interpretation(self, model_name, y_test, y_pred, y_proba, threshold, pr_auc):
        cm = confusion_matrix(y_test, y_pred)
        tn, fp, fn, tp = cm.ravel()

        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
        precision   = tp / (tp + fp) if (tp + fp) > 0 else 0
        accuracy    = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0
        f1          = 2 * (precision * sensitivity) / (precision + sensitivity) if (precision + sensitivity) > 0 else 0
        auc         = roc_auc_score(y_test, y_proba)

        # Build a structured dict matching the 5 dashboard MetricCards exactly
        metrics = {
            "AUC-ROC":   {"value": round(auc, 4),         "plain": f"The model correctly ranks a diabetic above a non-diabetic {auc*100:.1f}% of the time across all thresholds."},
            "F1 Score":  {"value": round(f1, 4),          "plain": f"Harmonic mean of Precision and Recall. Balances false positives and false negatives. Score: {f1*100:.1f}%."},
            "Precision": {"value": round(precision, 4),   "plain": f"When the model flags someone as diabetic, it is correct {precision*100:.1f}% of the time."},
            "Recall":    {"value": round(sensitivity, 4), "plain": f"Of all actual diabetic individuals, the model identified {sensitivity*100:.1f}%. It missed {(1-sensitivity)*100:.1f}%."},
            "Accuracy":  {"value": round(accuracy, 4),    "plain": f"Overall, {accuracy*100:.1f}% of predictions were correct. Note: misleading with imbalanced data."},
        }

        lines = [
            f"MODEL PERFORMANCE REPORT: {model_name.upper()}",
            f"Optimised Threshold: {threshold:.2f}",
            "=" * 50,
        ]
        for metric, data in metrics.items():
            lines.append(f"{metric}: {data['value']:.4f}")
            lines.append(f"  {data['plain']}")
            lines.append("")

        with open(os.path.join(self.run_dir, f"{model_name}_interpretation.txt"), "w") as f:
            f.write("\n".join(lines))

if __name__ == "__main__":
    trainer = ModelTrainer()
    trainer.run(balancing_method='class_weight', use_cached_params=True)
