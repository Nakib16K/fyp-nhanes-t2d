import { useState } from "react";
import { LocalSHAPResult } from "../../types";

interface SHAPVisualizationProps {
  result: LocalSHAPResult;
  alignRows?: boolean;
}

export function SHAPVisualization({ result, alignRows = false }: SHAPVisualizationProps) {
  const [showAll, setShowAll] = useState(false);
  const maxAbsValue = Math.max(
    ...result.shap_values_sorted.map((item) => Math.abs(item.impact)),
    0.0001
  );

  const featureData = result.shap_values_sorted.map((item) => ({
    name: item.feature,
    value: item.impact,
    percentage: (Math.abs(item.impact) / maxAbsValue) * 100,
    indicatorState: item.indicator_state,
  }));

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 space-y-6">
      <div>
        <h3 className="text-lg font-bold text-gray-900 mb-2">
          Local SHAP contributions (base estimator)
        </h3>
        <p className="text-sm text-gray-600">
          Displays diagnostic feature contributions from an uncalibrated
          estimator for model{" "}
          <span className="font-bold text-blue-700">{result.model}</span>.
          These are not an explanation of the calibrated probability or model threshold decision.
        </p>
      </div>

      <div className="space-y-4">
        {(showAll ? featureData : featureData.slice(0, 5)).map((feature) => (
          <div key={feature.name} className="space-y-1">
            <div className={`flex justify-between items-start gap-3${alignRows ? " min-h-[40px] lg:min-h-[76px] xl:min-h-[40px]" : ""}`}>
              <div className="min-w-0">
                <label className="block text-sm font-medium text-gray-700">
                  {feature.name}
                </label>
                {feature.indicatorState && (
                  <p className="mt-1 text-xs text-blue-800">
                    {feature.indicatorState === "present"
                      ? "Indicator selected / present"
                      : "Indicator not selected / absent"}
                  </p>
                )}
              </div>
              <span className="flex-shrink-0 text-sm font-semibold text-gray-900">
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

            <p className={`text-xs text-gray-500${alignRows ? " lg:min-h-[32px] xl:min-h-[16px]" : ""}`}>
              {feature.value > 0
                ? "Increased underlying estimator output"
                : feature.value < 0 ? "Decreased underlying estimator output"
                : "No measurable contribution at displayed precision"}
            </p>
          </div>
        ))}
      </div>

      {featureData.length > 5 && (
        <button type="button" onClick={() => setShowAll((v) => !v)}
          className="text-sm text-blue-700 font-medium underline hover:text-blue-900">
          {showAll ? "Show top 5 contributions" : `Show all ${featureData.length} contributions`}
        </button>
      )}

      {/* How to interpret */}
      <div className="mt-4 p-4 bg-blue-100 rounded-lg space-y-2">
        <p className="text-sm text-blue-900">
          <span className="font-semibold">How to interpret:</span> Positive SHAP
          values (Red) increase the underlying estimator's model-specific output;
          negative values (Green) decrease it. These values are not calibrated
          probability points and do not directly explain the final decision threshold.
          Bar length shows the magnitude of an estimator-level contribution.
        </p>
        <p className="text-sm text-blue-800">
          <span className="font-semibold">Note on categorical features:</span> For
          yes/no and category options are represented by encoded indicators. A bar for an option you did not choose
          (e.g. "Vigorous Activity: Yes" when you selected No) shows the effect of
          its <em>absence</em> on your prediction. This is expected and does not
          indicate an error.
        </p>
      </div>
    </div>
  );
}