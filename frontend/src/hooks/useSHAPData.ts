import { api } from "../utils/api";

export function useModelGlobalSHAPUrl(modelName: string) {
  return api.getModelGlobalShapUrl(modelName);
}
