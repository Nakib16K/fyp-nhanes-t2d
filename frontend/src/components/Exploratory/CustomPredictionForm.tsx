import { useState } from "react";
import { ChevronDown, ChevronUp, Info } from "lucide-react";
import { CustomPredictionInput, EDUCATION_LEVELS } from "../../types";
import { LoadingSpinner } from "../LoadingSpinner";
import { ErrorMessage } from "../ErrorMessage";
import { DisclaimerBanner } from "../DisclaimerBanner";

interface CustomPredictionFormProps {
  onSubmit: (input: CustomPredictionInput, modelName: string) => Promise<void>;
  isLoading?: boolean;
  error?: Error | null;
}

const MODEL_OPTIONS = ["XGB", "RF", "LGBM"] as const;

// Local form state uses string for numeric inputs so fields can be blank
// Only converted to numbers on submit
type FormState = {
  gender_code: number;
  age_years: string;
  ethnicity_code: number;
  education_level: number;
  poverty_ratio: string;
  height_cm: string;
  weight_kg: string;
  waist_circumference: string;
  systolic_bp: string;
  diastolic_bp: string;
  pulse_60s: string;
  history_high_bp: number;
  smoked_100_cigs: number;
  family_history_diabetes: number;
  vigorous_activity: number;
};

const EMPTY_FORM: FormState = {
  gender_code: 0,
  age_years: "",
  ethnicity_code: 0,
  education_level: 0,
  poverty_ratio: "",
  height_cm: "",
  weight_kg: "",
  waist_circumference: "",
  systolic_bp: "",
  diastolic_bp: "",
  pulse_60s: "",
  history_high_bp: 0,
  smoked_100_cigs: 0,
  family_history_diabetes: 0,
  vigorous_activity: 0,
};

export function CustomPredictionForm({
  onSubmit,
  isLoading,
  error,
}: CustomPredictionFormProps) {
  const [expanded, setExpanded] = useState(false);
  const [selectedModel, setSelectedModel] = useState<string>("XGB");
  const [formData, setFormData] = useState<FormState>(EMPTY_FORM);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};
    const age = Number(formData.age_years);
    const pr = Number(formData.poverty_ratio);
    const h = Number(formData.height_cm);
    const w = Number(formData.weight_kg);
    const wc = Number(formData.waist_circumference);
    const sbp = Number(formData.systolic_bp);
    const dbp = Number(formData.diastolic_bp);
    const pulse = Number(formData.pulse_60s);

    if (
      !formData.gender_code ||
      formData.gender_code === 0
    ) errors.gender_code = "Please select a gender";
    if (![1, 2, 3, 4, 6, 7].includes(formData.ethnicity_code))
      errors.ethnicity_code = "Select a supported ethnicity";
    if (![1, 2, 3, 4, 5].includes(formData.education_level))
      errors.education_level = "Select a supported education level (1–5)";
    if (
      !formData.history_high_bp ||
      formData.history_high_bp === 0
    ) errors.history_high_bp = "Please select an option";
    if (!formData.smoked_100_cigs || formData.smoked_100_cigs === 0) errors.smoked_100_cigs = "Please select an option";
    if (
      !formData.family_history_diabetes ||
      formData.family_history_diabetes === 0
    ) errors.family_history_diabetes = "Please select an option";
    if (
      !formData.vigorous_activity ||
      formData.vigorous_activity === 0
    ) errors.vigorous_activity = "Please select an option";

    if (
      formData.age_years === "" ||
      isNaN(age) ||
      age < 20 ||
      age > 120 ||
      !Number.isInteger(age)
    ) errors.age_years = "Must be a whole number (20–120)";
    if (
      formData.poverty_ratio === "" ||
      isNaN(pr) ||
      pr < 0 ||
      pr > 5
    ) errors.poverty_ratio = "Must be 0.0 – 5.0";
    if (
      formData.height_cm === "" ||
      isNaN(h) ||
      h < 100 ||
      h > 250
    ) errors.height_cm = "Must be 100–250 cm";
    if (
      formData.weight_kg === "" ||
      isNaN(w) ||
      w < 30 ||
      w > 300
    ) errors.weight_kg = "Must be 30–300 kg";
    if (
      formData.waist_circumference === "" ||
      isNaN(wc) ||
      wc < 50 ||
      wc > 200
    ) errors.waist_circumference = "Must be 50–200 cm";
    if (
      formData.systolic_bp === "" ||
      isNaN(sbp) ||
      sbp < 70 ||
      sbp > 250 ||
      !Number.isInteger(sbp)
    ) errors.systolic_bp = "Must be a whole number (70–250 mmHg)";
    if (
      formData.diastolic_bp === "" ||
      isNaN(dbp) ||
      dbp < 40 ||
      dbp > 150 ||
      !Number.isInteger(dbp)
    ) errors.diastolic_bp = "Must be a whole number (40–150 mmHg)";
    if (formData.pulse_60s === "" || isNaN(pulse) || pulse < 30 || pulse > 200 || !Number.isInteger(pulse)) errors.pulse_60s = "Must be a whole number (30–200 bpm)";

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;
    // Convert string fields to numbers for the API
    const payload: CustomPredictionInput = {
      gender_code: formData.gender_code,
      age_years: Number(formData.age_years),
      ethnicity_code: formData.ethnicity_code,
      education_level: formData.education_level,
      poverty_ratio: Number(formData.poverty_ratio),
      height_cm: Number(formData.height_cm),
      weight_kg: Number(formData.weight_kg),
      waist_circumference: Number(formData.waist_circumference),
      systolic_bp: Number(formData.systolic_bp),
      diastolic_bp: Number(formData.diastolic_bp),
      pulse_60s: Number(formData.pulse_60s),
      history_high_bp: formData.history_high_bp,
      smoked_100_cigs: formData.smoked_100_cigs,
      family_history_diabetes: formData.family_history_diabetes,
      vigorous_activity: formData.vigorous_activity,
    };
    await onSubmit(payload, selectedModel);
  };

  const handleNumericChange = (field: keyof FormState, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (validationErrors[field]) {
      setValidationErrors((prev) => { const n = { ...prev }; delete n[field]; return n; });
    }
  };

  const handleSelectChange = (field: keyof FormState, value: number) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (validationErrors[field]) {
      setValidationErrors((prev) => { const n = { ...prev }; delete n[field]; return n; });
    }
  };

  return (
    <div className="space-y-4">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-6 bg-blue-50 hover:bg-blue-100 transition-colors rounded-lg border border-blue-200 flex items-center justify-between"
      >
        <div className="text-left">
          <h3 className="font-bold text-gray-900">Test Your Own Prediction</h3>
          <p className="text-sm text-gray-600 mt-1">
            Explore research model estimates from an illustrative profile, not a diagnosis
          </p>
        </div>
        {expanded ? (
          <ChevronUp className="w-5 h-5 text-blue-600 flex-shrink-0" />
        ) : (
          <ChevronDown className="w-5 h-5 text-blue-600 flex-shrink-0" />
        )}
      </button>

      {expanded && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <form onSubmit={handleSubmit} className="space-y-8">

            {/* Model Selection */}
            <div className="space-y-4">
              <h4 className="font-semibold text-gray-900 border-b pb-2">Model Selection</h4>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Choose model for local SHAP explanation
                </label>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="w-full md:w-1/3 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600"
                >
                  {MODEL_OPTIONS.map((m) => <option key={m} value={m}>{m}</option>)}
                </select>
                <p className="text-xs text-gray-600 mt-2">
                  All four models provide predictions. This menu selects only the
                  model used for the feature explanation (LR has no local SHAP).
                </p>
              </div>
            </div>

            {/* Demographics */}
            <div className="space-y-4">
              <h4 className="font-semibold text-gray-900 border-b pb-2">Demographics</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Age (years)</label>
                  <input type="number" placeholder="e.g. 45"
                    value={formData.age_years}
                    onChange={(e) => handleNumericChange("age_years", e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600"
                  />
                  {validationErrors.age_years &&
                    <p className="text-red-600 text-xs mt-1">{validationErrors.age_years}</p>}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Gender</label>
                  <select value={formData.gender_code}
                    onChange={(e) => handleSelectChange("gender_code", parseInt(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600"
                  >
                    <option value={0} disabled>Select...</option>
                    <option value={1}>Male</option>
                    <option value={2}>Female</option>
                  </select>
                  {validationErrors.gender_code &&
                    <p className="text-red-600 text-xs mt-1">{validationErrors.gender_code}</p>}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Ethnicity</label>
                  <select value={formData.ethnicity_code}
                    onChange={(e) => handleSelectChange("ethnicity_code", parseInt(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600"
                  >
                    <option value={0} disabled>Select...</option>
                    <option value={1}>Mexican American</option>
                    <option value={2}>Other Hispanic</option>
                    <option value={3}>Non-Hispanic White</option>
                    <option value={4}>Non-Hispanic Black</option>
                    <option value={6}>Non-Hispanic Asian</option>
                    <option value={7}>Other / Multi-Racial</option>
                  </select>
                  {validationErrors.ethnicity_code &&
                    <p className="text-red-600 text-xs mt-1">{validationErrors.ethnicity_code}</p>}
                </div>

                <div className="md:col-span-2 lg:col-span-1">
                  <label className="block text-sm font-medium text-gray-700 mb-2">Education Level</label>
                  <select value={formData.education_level}
                    onChange={(e) => handleSelectChange("education_level", parseInt(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600"
                  >
                    <option value={0} disabled>Select...</option>
                    {Object.entries(EDUCATION_LEVELS).map(([code, label]) => (
                      <option key={code} value={parseInt(code)}>{label}</option>
                    ))}
                  </select>
                  {validationErrors.education_level &&
                    <p className="text-red-600 text-xs mt-1">{validationErrors.education_level}</p>}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-1.5">
                    Poverty Ratio (0.0 – 5.0)
                    <span className="relative group">
                      <Info className="w-3.5 h-3.5 text-gray-400 hover:text-blue-600 cursor-help" />
                      <span className="absolute left-0 bottom-6 w-64 z-10 hidden group-hover:block bg-gray-900 text-white text-xs rounded-lg p-2.5 leading-relaxed shadow-lg">
                        Ratio of household income to the federal poverty guideline.
                        Below 1.0 = below poverty line &bull; 1.0–2.0 = low income &bull; 3.0–5.0 = middle/higher income.
                        Use 5.0 if you are unsure.
                      </span>
                    </span>
                  </label>
                  <input type="number" step="0.1" placeholder="e.g. 2.5"
                    value={formData.poverty_ratio}
                    onChange={(e) => handleNumericChange("poverty_ratio", e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600"
                  />
                  {validationErrors.poverty_ratio &&
                    <p className="text-red-600 text-xs mt-1">{validationErrors.poverty_ratio}</p>}
                </div>
              </div>
            </div>

            {/* Body Measurements */}
            <div className="space-y-4">
              <h4 className="font-semibold text-gray-900 border-b pb-2 flex items-center gap-2">
                Body Measurements
                <span className="text-xs font-normal text-gray-500">(Height &amp; Weight are converted to BMI natively)</span>
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Height (cm)</label>
                  <input type="number" placeholder="e.g. 170"
                    value={formData.height_cm}
                    onChange={(e) => handleNumericChange("height_cm", e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600"
                  />
                  {validationErrors.height_cm &&
                    <p className="text-red-600 text-xs mt-1">{validationErrors.height_cm}</p>}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Weight (kg)</label>
                  <input type="number" placeholder="e.g. 75"
                    value={formData.weight_kg}
                    onChange={(e) => handleNumericChange("weight_kg", e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600"
                  />
                  {validationErrors.weight_kg &&
                    <p className="text-red-600 text-xs mt-1">{validationErrors.weight_kg}</p>}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Waist Circumference (cm)</label>
                  <input type="number" placeholder="e.g. 90"
                    value={formData.waist_circumference}
                    onChange={(e) => handleNumericChange("waist_circumference", e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600"
                  />
                  {validationErrors.waist_circumference &&
                    <p className="text-red-600 text-xs mt-1">{validationErrors.waist_circumference}</p>}
                </div>
              </div>
              {formData.height_cm !== "" && (Number(formData.height_cm) > 210 || Number(formData.height_cm) < 130) && (
                <p className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-md p-3" role="status">
                  Unusual height entered. Please double-check the measurement and units.
                  Research model estimates may be less reliable for uncommon profiles.
                </p>
              )}
            </div>

            {/* Vitals */}
            <div className="space-y-4">
              <h4 className="font-semibold text-gray-900 border-b pb-2">Vitals</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Systolic BP (mmHg)</label>
                  <input type="number" placeholder="e.g. 120"
                    value={formData.systolic_bp}
                    onChange={(e) => handleNumericChange("systolic_bp", e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600"
                  />
                  {validationErrors.systolic_bp &&
                    <p className="text-red-600 text-xs mt-1">{validationErrors.systolic_bp}</p>}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Diastolic BP (mmHg)</label>
                  <input type="number" placeholder="e.g. 80"
                    value={formData.diastolic_bp}
                    onChange={(e) => handleNumericChange("diastolic_bp", e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600"
                  />
                  {validationErrors.diastolic_bp &&
                    <p className="text-red-600 text-xs mt-1">{validationErrors.diastolic_bp}</p>}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Resting Pulse (bpm)</label>
                  <input type="number" placeholder="e.g. 72"
                    value={formData.pulse_60s}
                    onChange={(e) => handleNumericChange("pulse_60s", e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600"
                  />
                  {validationErrors.pulse_60s && <p className="text-red-600 text-xs mt-1">{validationErrors.pulse_60s}</p>}
                </div>
              </div>
            </div>

            {/* Lifestyle & History */}
            <div className="space-y-4">
              <h4 className="font-semibold text-gray-900 border-b pb-2">Lifestyle &amp; History</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">High BP History?</label>
                  <select value={formData.history_high_bp}
                    onChange={(e) => handleSelectChange("history_high_bp", parseInt(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600"
                  >
                    <option value={0} disabled>Select...</option>
                    <option value={1}>Yes</option>
                    <option value={2}>No</option>
                  </select>
                  {validationErrors.history_high_bp &&
                    <p className="text-red-600 text-xs mt-1">{validationErrors.history_high_bp}</p>}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Family Diabetes History?</label>
                  <select value={formData.family_history_diabetes}
                    onChange={(e) => handleSelectChange("family_history_diabetes", parseInt(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600"
                  >
                    <option value={0} disabled>Select...</option>
                    <option value={1}>Yes</option>
                    <option value={2}>No</option>
                  </select>
                  {validationErrors.family_history_diabetes &&
                    <p className="text-red-600 text-xs mt-1">{validationErrors.family_history_diabetes}</p>}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Smoked 100+ Cigarettes?</label>
                  <select value={formData.smoked_100_cigs}
                    onChange={(e) => handleSelectChange("smoked_100_cigs", parseInt(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600"
                  >
                    <option value={0} disabled>Select...</option>
                    <option value={1}>Yes</option>
                    <option value={2}>No</option>
                  </select>
                  {validationErrors.smoked_100_cigs && <p className="text-red-600 text-xs mt-1">{validationErrors.smoked_100_cigs}</p>}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Vigorous Physical Activity?</label>
                  <select value={formData.vigorous_activity}
                    onChange={(e) => handleSelectChange("vigorous_activity", parseInt(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600"
                  >
                    <option value={0} disabled>Select...</option>
                    <option value={1}>Yes</option>
                    <option value={2}>No</option>
                  </select>
                  {validationErrors.vigorous_activity &&
                    <p className="text-red-600 text-xs mt-1">{validationErrors.vigorous_activity}</p>}
                </div>
              </div>
            </div>

            <div className="space-y-4 pt-4 border-t border-gray-200">
              <DisclaimerBanner variant="privacy" />
              <DisclaimerBanner variant="general" />
            </div>

            {error && <ErrorMessage message={error.message} />}

            <button type="submit" disabled={isLoading}
              className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors font-medium"
            >
              {isLoading ? (
                <div className="flex items-center justify-center gap-2">
                  <LoadingSpinner /><span>Getting Prediction...</span>
                </div>
              ) : "Get Prediction"}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
