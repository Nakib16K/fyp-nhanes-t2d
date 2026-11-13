import { useState } from "react";
import { Info } from "lucide-react";
import { PresetProfile, PredictionResult, LocalSHAPResult } from "../../types";
import { LoadingSpinner } from "../LoadingSpinner";
import { SHAPVisualization } from "./SHAPVisualization";

interface PresetCardProps {
  name: string;
  preset: PresetProfile;
  prediction?: PredictionResult;
  shapResult?: LocalSHAPResult;
  shapLoading?: boolean;
  isLoading?: boolean;
  onPredict: () => void;
}

const PRESET_LABELS: Record<string, { name: string; description: string }> = {
  healthy: {
    name: "Lower-Risk-Factor Example",
    description: "Illustrative inputs with fewer conventional risk factors",
  },
  elevated_risk: {
    name: "Middle-Risk-Factor Example",
    description: "Illustrative inputs with several risk factors",
  },
  high_risk: {
    name: "Higher-Risk-Factor Example",
    description: "Illustrative inputs with multiple risk factors",
  },
};

// Human-readable labels for all current preset inputs
const VARIABLE_LABELS: Record<string, string> = {
  age_years:               "Age (years)",
  gender_code:             "Gender",
  ethnicity_code:          "Ethnicity",
  education_level:         "Education Level",
  poverty_ratio:           "Poverty Ratio",
  height_cm:               "Height (cm)",
  weight_kg:               "Weight (kg)",
  waist_circumference:     "Waist Circumference (cm)",
  systolic_bp:             "Systolic BP (mmHg)",
  diastolic_bp:            "Diastolic BP (mmHg)",
  pulse_60s:               "Resting Pulse (bpm)",
  history_high_bp:         "High BP History",
  smoked_100_cigs:         "Smoked 100+ Cigarettes",
  family_history_diabetes: "Family Diabetes History",
  vigorous_activity:       "Vigorous Activity",
};

const YES_NO_FIELDS = [
  "history_high_bp",
  "smoked_100_cigs",
  "family_history_diabetes",
  "vigorous_activity",
];
const GENDER_MAP: Record<number, string> = { 1: "Male", 2: "Female" };
const ETHNICITY_MAP: Record<number, string> = {
  1: "Mexican American", 2: "Other Hispanic", 3: "Non-Hispanic White",
  4: "Non-Hispanic Black", 6: "Non-Hispanic Asian",
  7: "Other / Multi-Racial",
};
const EDUCATION_MAP: Record<number, string> = {
  1: "Less than 9th grade", 2: "9–11th grade", 3: "High school / GED",
  4: "Some college / AA", 5: "College graduate or above",
};

function formatPresetValue(key: string, value: number): string {
  if (key === "gender_code") return GENDER_MAP[value] ?? String(value);
  if (key === "ethnicity_code") return ETHNICITY_MAP[value] ?? String(value);
  if (key === "education_level") return EDUCATION_MAP[value] ?? String(value);
  if (YES_NO_FIELDS.includes(key)) return value === 1 ? "Yes" : "No";
  return String(value);
}

export function PresetCard({
  name,
  preset,
  prediction,
  shapResult,
  shapLoading,
  isLoading,
  onPredict,
}: PresetCardProps) {
  const [showInfo, setShowInfo] = useState(false);
  const [showShap, setShowShap] = useState(false);

  const label = PRESET_LABELS[name] || { name, description: "" };
  const bmi = preset.weight_kg / ((preset.height_cm / 100) ** 2);

  const scores = prediction
    ? Object.values(prediction.predictions).map((p) => p.probability_score)
    : [];
  const avgEstimate = scores.length === 4 && scores.every(Number.isFinite)
    ? scores.reduce((sum, p) => sum + p, 0) / 4
    : null;

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden bg-white flex flex-col">
      {/* Header */}
      <div className="p-6 bg-gradient-to-r from-gray-50 to-white flex items-start justify-between">
        <div>
          <h3 className="text-lg font-bold text-gray-900">{label.name}</h3>
          <p className="text-sm text-gray-600 mt-1 min-h-[40px]">{label.description}</p>
        </div>
        {/* Info button — shows current variables */}
        <button
          onClick={() => setShowInfo(!showInfo)}
          title="Show all variable values"
          className="ml-3 mt-0.5 p-1.5 rounded-full text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition-colors flex-shrink-0"
        >
          <Info className="w-4 h-4" />
        </button>
      </div>

      {/* Info panel — all current inputs */}
      {showInfo && (
        <div className="px-6 pb-4 border-t border-gray-100 bg-gray-50">
          <p className="text-xs font-semibold text-gray-500 uppercase mt-3 mb-2">All Variable Values</p>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
            {Object.entries(preset).map(([key, value]) => (
              <div key={key} className="flex justify-between">
                <span className="text-gray-600">{VARIABLE_LABELS[key] ?? key}:</span>
                <span className="font-medium text-gray-900 ml-2">{formatPresetValue(key, value as number)}</span>
              </div>
            ))}
            <div className="flex justify-between">
              <span className="text-gray-600">BMI (computed):</span>
              <span className="font-medium text-gray-900 ml-2">{bmi.toFixed(1)}</span>
            </div>
          </div>
        </div>
      )}

      <div className="p-6 space-y-4 flex-1">
        {/* Summary stats */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-gray-600 uppercase font-semibold">Age</p>
            <p className="text-lg font-semibold text-gray-900">{preset.age_years} years</p>
          </div>
          <div>
            <p className="text-xs text-gray-600 uppercase font-semibold">BMI</p>
            <p className="text-lg font-semibold text-gray-900">{bmi.toFixed(1)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-600 uppercase font-semibold">BP</p>
            <p className="text-lg font-semibold text-gray-900">
              {preset.systolic_bp}/{preset.diastolic_bp}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-600 uppercase font-semibold">Waist</p>
            <p className="text-lg font-semibold text-gray-900">{preset.waist_circumference} cm</p>
          </div>
        </div>

        {/* Get Prediction button */}
        {!prediction && (
          <button
            onClick={onPredict}
            disabled={isLoading}
            className="w-full mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors font-medium"
          >
            {isLoading ? "Predicting..." : "Get Prediction"}
          </button>
        )}

        {isLoading && (
          <div className="py-4">
            <LoadingSpinner />
          </div>
        )}

        {/* Prediction results */}
        {prediction && (
          <>
            <div className="p-4 rounded-lg bg-blue-50 border border-blue-100">
              <p className="text-xs text-gray-700 uppercase font-semibold mb-2">
                Illustrative arithmetic mean of four model estimates
              </p>
              <p className="text-2xl font-bold text-blue-900">
                {avgEstimate === null ? "Unavailable" : `${(avgEstimate * 100).toFixed(1)}%`}
              </p>
              <p className="text-xs text-gray-700 mt-1">
                Not a validated ensemble probability or a clinical risk score.
                A displayed 0.0% is rounding, not zero disease risk.
              </p>
              <div className="mt-4 space-y-2">
                {Object.entries(prediction.predictions).map(([modelName, pred]) => (
                  <div key={modelName} className="text-sm space-y-0.5">
                    <div><span className="font-medium">{modelName}:</span>{" "}
                      <span className="text-blue-800">{pred.risk_percentage}</span></div>
                    <p className="text-xs text-gray-700">
                      {typeof pred.above_threshold === "boolean"
                        ? pred.above_threshold ? "Above model threshold" : "Below model threshold"
                        : "Decision flag unavailable"}
                      {typeof pred.decision_threshold === "number" &&
                        ` · Cutoff ${(pred.decision_threshold * 100).toFixed(2)}%`}
                    </p>
                  </div>
                ))}
              </div>
              <p className="text-xs text-gray-600 mt-3">
                Each threshold was selected on validation data for that individual model.
                It is not a medical cutoff; model flags may disagree.
              </p>
            </div>

            {/* SHAP toggle button */}
            <button
              onClick={() => setShowShap(!showShap)}
              className="w-full px-4 py-2 border border-blue-300 text-blue-700 rounded-lg hover:bg-blue-50 transition-colors text-sm font-medium"
            >
              {showShap ? "Hide Feature Explanation" : "Show Feature Explanation (XGB)"}
            </button>

            {/* SHAP loading */}
            {shapLoading && showShap && (
              <div className="flex items-center justify-center py-4">
                <div className="space-y-2 text-center">
                  <LoadingSpinner />
                  <p className="text-xs text-gray-500">Generating explanation...</p>
                </div>
              </div>
            )}

            {/* SHAP visualization */}
            {shapResult && showShap && !shapLoading && (
              <SHAPVisualization result={shapResult} alignRows />
            )}
          </>
        )}
      </div>
    </div>
  );
}
