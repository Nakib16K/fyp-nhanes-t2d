import { 
  CustomPredictionInput, 
  LocalSHAPResult, 
  PredictionResult, 
  ModelMetrics,
  PresetProfile
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
// Session timestamp for cache-busting static assets (SHAP images etc.)
const SESSION_TS = Date.now();

export async function fetchJSON<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

export const api = {
  healthCheck: () => fetchJSON<{status: string, models_loaded: string[]}>("/health"),

  getAllModelsMetrics: () => fetchJSON<ModelMetrics[]>("/api/models/metrics"),

  getModelGlobalShapUrl: (modelName: string) =>
    `${API_BASE_URL}/api/models/${modelName}/shap/global?t=${SESSION_TS}`,

  getPresets: () => fetchJSON<Record<string, PresetProfile>>(`/api/exploratory/presets?t=${SESSION_TS}`),

  predictCustom: (input: CustomPredictionInput | PresetProfile) =>
    fetchJSON<PredictionResult>("/api/exploratory/predict/custom", {
      method: "POST",
      body: JSON.stringify(input),
    }),

  getLocalShap: (modelName: string, input: CustomPredictionInput | PresetProfile) =>
    fetchJSON<LocalSHAPResult>(`/api/exploratory/predict/custom/shap/${modelName}`, {
      method: "POST",
      body: JSON.stringify(input),
    }),

  // Fetches the plain-text interpretation file for a given model
  getModelInterpretation: async (modelName: string): Promise<string> => {
    const response = await fetch(`${API_BASE_URL}/api/models/${modelName}/interpretation`);
    if (!response.ok) throw new Error("Interpretation not available");
    return response.text();
  },
};