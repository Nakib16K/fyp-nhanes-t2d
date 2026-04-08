import { LocalSHAPResult } from "../../types";

interface SHAPVisualizationProps {
  result: LocalSHAPResult;
}

export function SHAPVisualization({ result }: SHAPVisualizationProps) {
  const maxAbsValue = Math.max(
    ...result.shap_values_sorted.map((item) => Math.abs(item.impact)),
    0.0001
  );

  const featureData = result.shap_values_sorted.map((item) => ({
    name: item.feature,
    value: item.impact,
    percentage: (Math.abs(item.impact) / maxAbsValue) * 100,
  }));

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 space-y-6">
      <div>
        <h3 className="text-lg font-bold text-gray-900 mb-2">
          Feature Importance (Local SHAP Values)
        </h3>
        <p className="text-sm text-gray-600">
          Shows how your specific health metrics influenced the prediction for model{" "}
          <span className="font-bold text-blue-700">{result.model}</span>
        </p>
      </div>

      <div className="space-y-4">
        {featureData.map((feature) => (
          <div key={feature.name} className="space-y-1">
            <div className="flex justify-between items-center">
              <label className="text-sm font-medium text-gray-700">
                {feature.name}
              </label>
              <span className="text-sm font-semibold text-gray-900">
                {feature.value.toFixed(4)}
              </span>
            </div>

            {/* Progress Bar */}
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden flex">
              <div
                className={`h-full transition-all duration-500 ease-out ${
                  feature.value > 0 ? "bg-red-500" : "bg-green-500"
                }`}
                style={{ width: `${feature.percentage}%` }}
              />
            </div>

            <p className="text-xs text-gray-500">
              {feature.value > 0
                ? "Increased your risk score"
                : "Decreased your risk score"}
            </p>
          </div>
        ))}
      </div>

      {/* How to interpret */}
      <div className="mt-4 p-4 bg-blue-100 rounded-lg space-y-2">
        <p className="text-sm text-blue-900">
          <span className="font-semibold">How to interpret:</span> Positive SHAP
          values (Red) push your prediction towards "High Risk", while negative values
          (Green) push it towards "Low Risk". The length of each bar shows the magnitude
          of that specific feature's impact.
        </p>
        <p className="text-sm text-blue-800">
          <span className="font-semibold">Note on categorical features:</span> For
          yes/no and category options, the model evaluates every possible answer —
          including options you did not select. A bar for an option you did not choose
          (e.g. "Vigorous Activity: Yes" when you selected No) shows the effect of
          its <em>absence</em> on your prediction. This is expected and does not
          indicate an error.
        </p>
      </div>
    </div>
  );
}