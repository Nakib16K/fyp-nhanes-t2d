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
  const headers = new Headers(options?.headers);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const method = (options?.method || "GET").toUpperCase();
  if (method === "POST" || method === "PUT") {
    const body = options?.body ?? "";
    if (typeof body !== "string") {
      throw new Error("Signed API requests require a string body.");
    }
    if (!globalThis.crypto?.subtle) {
      throw new Error("Secure request hashing requires HTTPS or localhost.");
    }
    // CloudFront signs the request; this hash covers the exact UTF-8 body sent.
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(body));
    headers.set("x-amz-content-sha256", Array.from(new Uint8Array(digest))
      .map(value => value.toString(16).padStart(2, "0")).join(""));
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
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
