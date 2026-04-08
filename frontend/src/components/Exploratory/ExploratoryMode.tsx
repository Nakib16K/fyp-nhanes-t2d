import { useState } from "react";
import { usePresets } from "../../hooks/usePresets";
import { CustomPredictionInput, PredictionResult, LocalSHAPResult } from "../../types";
import { api } from "../../utils/api";
import { LoadingSpinner } from "../LoadingSpinner";
import { ErrorMessage } from "../ErrorMessage";
import { PresetCard } from "./PresetCard";
import { CustomPredictionForm } from "./CustomPredictionForm";
import { DisclaimerBanner } from "../DisclaimerBanner";
import { SHAPVisualization } from "./SHAPVisualization";

export function ExploratoryMode() {
  const {
    presets,
    presetsLoading,
    presetsError,
    presetPredictions,
    predictionsLoading,
    predictionsError,
    predictPreset,
    presetShapResults,
    presetShapLoading,
  } = usePresets();

  const [customPrediction, setCustomPrediction] = useState<PredictionResult | null>(null);
  const [customPredictionError, setCustomPredictionError] = useState<Error | null>(null);
  const [customPredictionLoading, setCustomPredictionLoading] = useState(false);
  const [shapExplanation, setShapExplanation] = useState<LocalSHAPResult | null>(null);
  const [shapLoading, setShapLoading] = useState(false);

  const handleCustomPrediction = async (input: CustomPredictionInput, modelName: string) => {
    setCustomPredictionLoading(true);
    setCustomPredictionError(null);
    setShapExplanation(null);
    try {
      const result = await api.predictCustom(input);
      setCustomPrediction(result);

      setShapLoading(true);
      try {
        const shap = await api.getLocalShap(modelName, input);
        setShapExplanation(shap);
      } catch (shapError) {
        console.error("SHAP explanation failed:", shapError);
      } finally {
        setShapLoading(false);
      }
    } catch (error) {
      setCustomPredictionError(
        error instanceof Error ? error : new Error(String(error))
      );
    } finally {
      setCustomPredictionLoading(false);
    }
  };

  if (presetsLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner />
      </div>
    );
  }

  if (presetsError) {
    return <ErrorMessage message="Failed to load presets" />;
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Exploratory Mode</h1>
        <p className="text-gray-600 mt-2">
          Explore diabetes risk predictions with preset scenarios or your own health metrics
        </p>
      </div>

      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Preset Scenarios</h2>

        {presetsError && <ErrorMessage message="Failed to load preset scenarios" />}
        {predictionsError && <ErrorMessage message={`Prediction failed: ${predictionsError.message}`} />}

        {presets && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {Object.entries(presets).map(([key, preset]) => (
              <PresetCard
                key={key}
                name={key}
                preset={preset}
                prediction={presetPredictions[key]}
                shapResult={presetShapResults[key]}
                shapLoading={presetShapLoading[key]}
                isLoading={predictionsLoading && !(key in presetPredictions)}
                onPredict={() => predictPreset(key, preset)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Custom prediction section */}
      <div className="border-t border-gray-200 pt-8">
        <CustomPredictionForm
          onSubmit={handleCustomPrediction}
          isLoading={customPredictionLoading}
          error={customPredictionError}
        />

        {customPrediction && (
          <div className="mt-6 space-y-6">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 space-y-4">
              <h3 className="text-lg font-bold text-blue-900">Your Prediction Results</h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-blue-700 font-medium mb-1">BMI</p>
                  <p className="text-xl font-bold text-blue-900">
                    {customPrediction.computed_metrics.bmi}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-blue-700 font-medium mb-1">Waist-to-Height Ratio</p>
                  <p className="text-xl font-bold text-blue-900">
                    {customPrediction.computed_metrics.waist_to_height_ratio}
                  </p>
                </div>
              </div>

              <div className="mt-4 pt-4 border-t border-blue-300">
                <h4 className="font-semibold text-blue-900 mb-3">Model Predictions</h4>
                <div className="space-y-3">
                  {Object.entries(customPrediction.predictions).map(([modelName, pred]) => (
                    <div key={modelName} className="bg-white rounded-lg p-4 border border-blue-200">
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="font-bold text-gray-900">{modelName}</p>
                          <p className="text-sm text-gray-600">{pred.prediction_class}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-2xl font-bold text-blue-900">{pred.risk_percentage}</p>
                          <p className="text-xs text-gray-600">Probability: {pred.probability_score}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-4 pt-4 border-t border-blue-300 space-y-2">
                <p className="text-sm text-blue-800">
                  These predictions are from multiple machine learning models trained on diabetes risk factors.
                </p>
                <p className="text-sm text-blue-800">
                  <span className="font-semibold">Important:</span> This is an exploratory tool and should
                  not be used for medical diagnosis. Always consult a healthcare provider.
                </p>
              </div>
            </div>

            {shapLoading && (
              <div className="flex items-center justify-center py-6">
                <div className="space-y-3 text-center">
                  <LoadingSpinner />
                  <p className="text-sm text-gray-600">Generating feature explanations...</p>
                </div>
              </div>
            )}

            {shapExplanation && !shapLoading && (
              <SHAPVisualization result={shapExplanation} />
            )}
          </div>
        )}
      </div>

      <div className="mt-8 pt-8 border-t border-gray-200">
        <DisclaimerBanner variant="general" />
      </div>
    </div>
  );
}