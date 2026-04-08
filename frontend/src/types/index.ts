export interface ModelMetrics {
  model_name: string;
  auc_roc: number;
  precision: number;
  recall: number;
  f1: number;
  sensitivity: number;
  accuracy: number;
}

export interface SHAPFeature {
  feature: string;
  impact: number;
}

export interface SHAPData {
  model_name: string;
  feature_names: string[];
  shap_values: number[];
}

export interface LocalSHAPResult {
  model: string;
  shap_values_sorted: SHAPFeature[];
  base_value: number;
}

export interface PresetProfile {
  age_years: number;
  gender_code: number;
  ethnicity_code: number;
  education_level: number;
  poverty_ratio: number;
  height_cm: number;
  weight_kg: number;
  waist_circumference: number;
  systolic_bp: number;
  diastolic_bp: number;
  pulse_60s: number;
  history_high_bp: number;
  smoked_100_cigs: number;
  family_history_diabetes: number;
  vigorous_activity: number;
  alcohol_frequency: number;
}

export interface CustomPredictionInput {
  gender_code: number;
  age_years: number;
  ethnicity_code: number;
  education_level: number;
  poverty_ratio: number;
  height_cm: number;
  weight_kg: number;
  waist_circumference: number;
  systolic_bp: number;
  diastolic_bp: number;
  pulse_60s: number;
  history_high_bp: number;
  smoked_100_cigs: number;
  family_history_diabetes: number;
  vigorous_activity: number;
  alcohol_frequency: number;
}

export interface ModelPrediction {
  probability_score: number;
  risk_percentage: string;
  prediction_class: string;
  error?: string;
}

export interface PredictionResult {
  status: string;
  computed_metrics: {
    bmi: number;
    waist_to_height_ratio: number;
  };
  predictions: {
    [modelName: string]: ModelPrediction;
  };
}

export const EDUCATION_LEVELS = {
  1: "Less than 9th grade",
  2: "9-11th grade (Includes 12th grade with no diploma)",
  3: "High school graduate/GED or equivalent",
  4: "Some college or AA degree",
  5: "College graduate or above",
  7: "Refused",
  9: "Don't know",
} as const;

export type EducationLevel = keyof typeof EDUCATION_LEVELS;
