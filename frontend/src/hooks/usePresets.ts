import { api } from "../utils/api";
import { PresetProfile, PredictionResult, LocalSHAPResult } from "../types";
import { useAsync } from "./useAsync";
import { useState } from "react";

export function usePresets() {
  const [presetPredictions, setPresetPredictions] = useState<
    Record<string, PredictionResult>
  >({});
  const [predictionsLoading, setPredictionsLoading] = useState(false);
  const [predictionsError, setError] = useState<Error | null>(null);

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

  // FIX: Accept the preset object directly instead of looking it up from
  // presetsState.data inside the async function. This avoids the stale
  // closure problem where presetsState.data may not be current when
  // the function executes.
  const predictPreset = async (presetName: string, preset: PresetProfile) => {
    setPredictionsLoading(true);
    setError(null);
    try {
      const result = await api.predictCustom(preset);
      setPresetPredictions((prev) => ({
        ...prev,
        [presetName]: result,
      }));

      // Fetch local SHAP after prediction succeeds (XGB default)
      setPresetShapLoading((prev) => ({ ...prev, [presetName]: true }));
      try {
        const shapResult = await api.getLocalShap("XGB", preset);
        setPresetShapResults((prev) => ({ ...prev, [presetName]: shapResult }));
      } catch (shapError) {
        console.error(`SHAP for preset ${presetName} failed:`, shapError);
        // Non-blocking: prediction still shows even if SHAP fails
      } finally {
        setPresetShapLoading((prev) => ({ ...prev, [presetName]: false }));
      }

    } catch (error) {
      setError(error instanceof Error ? error : new Error(String(error)));
    } finally {
      setPredictionsLoading(false);
    }
  };

  return {
    presets: presetsState.data,
    presetsLoading: presetsState.isLoading,
    presetsError: presetsState.error,
    presetPredictions,
    predictionsLoading,
    predictionsError,
    predictPreset,
    presetShapResults,
    presetShapLoading,
  };
}