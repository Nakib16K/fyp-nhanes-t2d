import { useState } from "react";
import { useModelMetrics } from "../../hooks/useModelMetrics";
import { ModelMetrics } from "../../types";
import { LoadingSpinner } from "../LoadingSpinner";
import { ErrorMessage } from "../ErrorMessage";
import { MetricsChart } from "./MetricsChart";
import { ModelCard } from "./ModelCard";
import { DisclaimerBanner } from "../DisclaimerBanner";

type MetricKey = keyof Omit<ModelMetrics, "model_name" | "sensitivity">;

export function ModelComparisonMode() {
  const [primaryMetric, setPrimaryMetric] = useState<MetricKey>("auc_roc");
  const { data: models, isLoading: modelsLoading, error: modelsError } = useModelMetrics();

  if (modelsLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner />
      </div>
    );
  }

  if (modelsError) {
    return <ErrorMessage message="Failed to load model metrics" />;
  }

  return (
    <div className="space-y-8">
      <div>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Model Comparison</h1>
            <p className="text-gray-600 mt-2">
              Evaluate and compare all four diabetes prediction models
            </p>
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <label className="block text-sm font-medium text-gray-700 mb-4">
            Primary Metric
          </label>
          <select
            value={primaryMetric}
            onChange={(e) => setPrimaryMetric(e.target.value as MetricKey)}
            className="w-full md:w-48 px-4 py-2 border border-gray-300 rounded-lg bg-white text-gray-900 focus:ring-2 focus:ring-blue-600 focus:border-transparent"
          >
            <option value="auc_roc">AUC-ROC</option>
            <option value="f1">F1 Score</option>
            <option value="precision">Precision</option>
            <option value="recall">Recall (Sensitivity)</option>
            <option value="accuracy">Accuracy</option>
          </select>

          <div className="mt-8">
            {models && <MetricsChart models={models} metricKey={primaryMetric} />}
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <h2 className="text-2xl font-bold text-gray-900">Model Details</h2>
        {models?.map((model, index) => (
          <ModelCard
            key={model.model_name ?? index}
            model={model}
          />
        ))}
      </div>

      <div className="mt-8 pt-8 border-t border-gray-200">
        <DisclaimerBanner variant="general" />
      </div>
    </div>
  );
}