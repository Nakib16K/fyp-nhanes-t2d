import { ModelMetrics } from "../../types";

interface MetricsChartProps {
  models: ModelMetrics[];
  metricKey: keyof Omit<ModelMetrics, "model_name">;
}

export function MetricsChart({ models, metricKey }: MetricsChartProps) {
  if (!models || models.length === 0) {
    return (
      <div className="text-center py-8 text-gray-600">
        No model metrics available
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {models.map((model) => {
        const value = model?.[metricKey];
        const numValue = typeof value === 'number' ? value : 0;
        const percentage = numValue * 100;

        return (
          <div key={model?.model_name || Math.random()}>
            <div className="flex justify-between items-center mb-2">
              <span className="font-medium text-gray-900">
                {model?.model_name || "Unknown Model"}
              </span>
              <span className="text-sm font-semibold text-blue-600">
                {numValue.toFixed(3)}
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${percentage}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
