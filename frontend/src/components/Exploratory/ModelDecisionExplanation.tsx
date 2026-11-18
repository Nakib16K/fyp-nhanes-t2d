import { ModelPrediction } from "../../types";

interface Props {
  modelName: string;
  prediction: ModelPrediction;
}

// The backend compares full-precision values. Never recalculate the decision
// from probability_score or risk_percentage: both are rounded for display.
export function ModelDecisionExplanation({ modelName, prediction }: Props) {
  const hasDecision = typeof prediction.above_threshold === "boolean";
  const hasCutoff = typeof prediction.decision_threshold === "number" &&
    Number.isFinite(prediction.decision_threshold);
  const margin = prediction.decision_margin_pp;
  const hasMargin = typeof margin === "number" && Number.isFinite(margin);
  const isNearCutoff = hasMargin && Math.abs(margin) <= 0.1;

  const probabilityPercent = prediction.probability_score * 100;
  const cutoffPercent = (prediction.decision_threshold ?? 0) * 100;
  const safePercent = (v: number) => `${Math.min(100, Math.max(0, v))}%`;

  return (
    <div className="bg-white rounded-lg p-4 border border-blue-200 space-y-2">
      <div className="flex flex-wrap justify-between items-start gap-2">
        <div>
          <p className="font-bold text-gray-900">{modelName}</p>
          <p className="text-sm text-gray-700">
            {hasDecision
              ? prediction.above_threshold
                ? "Above model threshold"
                : "Below model threshold"
              : "Decision flag unavailable"}
          </p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold text-blue-900">{prediction.risk_percentage}</p>
          <p className="text-xs text-gray-600">Model estimate (rounded)</p>
        </div>
      </div>
      {hasCutoff && (
        <>
          <div className="relative h-3 rounded-full bg-slate-200" role="img"
            aria-label={`${modelName}: estimated score ${prediction.risk_percentage}; model threshold ${cutoffPercent.toFixed(2)} percent`}>
            <div className="h-full rounded-full bg-blue-500" style={{ width: safePercent(probabilityPercent) }} />
            <div className="absolute -top-1 h-5 w-0.5 bg-slate-900"
              style={{ left: safePercent(cutoffPercent) }} title="Model decision threshold" />
          </div>
          <p className="text-xs text-gray-700">Validation-selected cutoff: <strong>{cutoffPercent.toFixed(2)}%</strong>
            {hasMargin && <span> · Difference: {margin >= 0 ? "+" : ""}{margin.toFixed(3)} percentage points</span>}
          </p>
          {isNearCutoff && <p className="text-xs text-amber-800">
            Near the model's decision cutoff. The flag uses the full-precision score,
            not the rounded percentage shown above.
          </p>}
        </>
      )}
    </div>
  );
}
