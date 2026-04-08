import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.pipeline import ModelTrainer

def main():
    """
    Main Entry Point.
    """
    print("==================================================")
    print("   STARTING T2D DIABETES PREDICTION PIPELINE")
    print("==================================================")
    
    try:
        trainer = ModelTrainer()
        
        # BALANCING MODE SELECTION:
        # 'smote'       : Oversample minority class via SMOTE, disable class_weight
        # 'class_weight': Use cost-sensitive learning, no SMOTE resampling
        # 'undersample' : Undersample majority class, disable class_weight
        BALANCING_MODE = 'class_weight' 
        
        # CACHING MODE SELECTION:
        # True  : Fast-track mode. Loads previously saved optimal parameters if they exist, 
        #         bypassing the 50-trial Optuna search to save compute time.
        # False : Force a full Optuna Bayesian search, even if a cache exists.
        USE_CACHED_PARAMS = True 
        
        trainer.run(balancing_method=BALANCING_MODE, use_cached_params=USE_CACHED_PARAMS)
        
        print("\n==================================================")
        print("   PIPELINE COMPLETED SUCCESSFULLY")
        print("==================================================")
        print(f"Check the 'models/' folder for artifacts.")
        
    except Exception as e:
        print(f"\n[ERROR] Pipeline Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()