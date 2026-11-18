import { api } from "../utils/api";
import { PresetProfile, PredictionResult, LocalSHAPResult } from "../types";
import { useAsync } from "./useAsync";
import { useRef, useState } from "react";

function withoutProfile<T>(values: Record<string, T>, name: string): Record<string, T> {
  const next = { ...values };
  delete next[name];
  return next;
}

export function usePresets() {
  const [presetPredictions, setPresetPredictions] = useState<
    Record<string, PredictionResult>
  >({});
  const [presetPredictionLoading, setPresetPredictionLoading] = useState<Record<string, boolean>>({});
  const [presetPredictionErrors, setPresetPredictionErrors] = useState<Record<string, Error>>({});
  const [presetShapErrors, setPresetShapErrors] = useState<Record<string, Error>>({});
  const requestVersions = useRef<Record<string, number>>({});

  // SHAP state for presets
  const [presetShapResults, setPresetShapResults] = useState<
    Record<string, LocalSHAPResult>
  >({});
  const [presetShapLoading, setPresetShapLoading] = useState<
    Record<string, boolean>
  >({});

  const presetsState = useAsync<Record<string, PresetProfile>>(() =>
    api.getPresets()
  );

  const predictPreset = async (presetName: string, preset: PresetProfile) => {
    const version = (requestVersions.current[presetName] || 0) + 1;
    requestVersions.current[presetName] = version;
    const isCurrent = () => requestVersions.current[presetName] === version;
    setPresetPredictions((prev) => withoutProfile(prev, presetName));
    setPresetShapResults((prev) => withoutProfile(prev, presetName));
    setPresetPredictionErrors((prev) => withoutProfile(prev, presetName));
    setPresetShapErrors((prev) => withoutProfile(prev, presetName));
    setPresetShapLoading((prev) => ({ ...prev, [presetName]: false }));
    setPresetPredictionLoading((prev) => ({ ...prev, [presetName]: true }));
    try {
      const result = await api.predictCustom(preset);
      if (!isCurrent()) return;
      setPresetPredictions((prev) => ({
        ...prev,
        [presetName]: result,
      }));

      // Fetch local SHAP after prediction succeeds (XGB default)
      setPresetShapLoading((prev) => ({ ...prev, [presetName]: true }));
      try {
        const shapResult = await api.getLocalShap("XGB", preset);
        if (isCurrent()) setPresetShapResults((prev) => ({ ...prev, [presetName]: shapResult }));
      } catch {
        if (isCurrent()) setPresetShapErrors((prev) => ({
          ...prev,
          [presetName]: new Error("Prediction available, but the local explanation could not be generated. Please try again."),
        }));
      } finally {
        if (isCurrent()) setPresetShapLoading((prev) => ({ ...prev, [presetName]: false }));
      }

    } catch {
      if (isCurrent()) setPresetPredictionErrors((prev) => ({
        ...prev,
        [presetName]: new Error("Prediction unavailable. Please try again."),
      }));
    } finally {
      if (isCurrent()) setPresetPredictionLoading((prev) => ({ ...prev, [presetName]: false }));
    }
  };

  return {
    presets: presetsState.data,
    presetsLoading: presetsState.isLoading,
    presetsError: presetsState.error,
    presetPredictions,
    predictionsLoading: Object.values(presetPredictionLoading).some(Boolean),
    predictionsError: Object.values(presetPredictionErrors)[0] || null,
    presetPredictionLoading,
    presetPredictionErrors,
    presetShapErrors,
    predictPreset,
    presetShapResults,
    presetShapLoading,
  };
}
