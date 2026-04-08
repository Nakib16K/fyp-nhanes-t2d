import { api } from "../utils/api";
import { ModelMetrics } from "../types";
import { useAsync } from "./useAsync";

export function useModelMetrics() {
  return useAsync<ModelMetrics[]>(() => api.getAllModelsMetrics());
}