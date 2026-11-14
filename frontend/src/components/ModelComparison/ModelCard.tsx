import { useState } from "react";
import { ChevronDown, ChevronUp, Info, X } from "lucide-react";
import { ModelMetrics } from "../../types";
import { TabSelector } from "../TabSelector";
import { MetricCard } from "../MetricCard";
import { useModelGlobalSHAPUrl } from "../../hooks/useSHAPData";
import { api } from "../../utils/api";

interface ModelCardProps {
  model: ModelMetrics;
}

// Plain-English interpretations matching the 5 dashboard metrics exactly
const METRIC_EXPLANATIONS: Record<string, { title: string; plain: string }> = {
  "AUC-ROC": {
    title: "AUC-ROC — Ranking Ability",
    plain:
      "Measures how well scores rank proxy-positive test records above proxy-negative records. A score of 1.0 is perfect ranking; 0.5 is random ranking. This evaluates the survey-defined label, not a confirmed clinical diagnosis.",
  },
  "F1 Score": {
    title: "F1 Score — Balance",
    plain:
      "The harmonic mean of precision and recall for the positive survey label. Read it alongside both component metrics; it does not encode clinical error costs.",
  },
  Precision: {
    title: "Precision — Positive-Label Agreement",
    plain:
      "Among records predicted positive, the proportion with a positive survey-defined label. This describes agreement in the evaluated sample, not diagnostic certainty for an individual.",
  },
  Recall: {
    title: "Recall (Sensitivity) — Positive-Label Coverage",
    plain:
      "Among proxy-positive test records, the proportion predicted positive. It reports test-set sensitivity for the survey-defined label and does not establish clinical screening performance.",
  },
  Accuracy: {
    title: "Accuracy — Overall Correctness",
    plain:
      "The proportion of test predictions matching their survey-defined labels. Accuracy can be high when the common class dominates, so interpret it with per-class metrics.",
  },
};

export function ModelCard({ model }: ModelCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState("metrics");
  const [interpretationData, setInterpretationData] = useState<string | null>(null);
  const [showInterpretation, setShowInterpretation] = useState(false);

  const modelNameSafe = model?.model_name?.toLowerCase() || "";
  const globalShapUrl = useModelGlobalSHAPUrl(modelNameSafe);

  const tabs = [
    { id: "metrics", label: "Evaluation Metrics" },
    { id: "shap", label: "Global SHAP" },
  ];

  const handleInfoClick = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (showInterpretation) {
      setShowInterpretation(false);
      return;
    }
    // Try to fetch interpretation from API if not loaded
    if (!interpretationData) {
      try {
        const text = await api.getModelInterpretation(modelNameSafe);
        setInterpretationData(text);
      } catch {
        // Fallback to built-in explanations if API unavailable
        setInterpretationData("__builtin__");
      }
    }
    setShowInterpretation(true);
  };

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden bg-white">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-6 hover:bg-gray-50 transition-colors text-left"
      >
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-gray-900">{model?.model_name || "Unknown Model"}</h3>
            <p className="text-sm text-gray-600 mt-1">
              AUC-ROC: {model?.auc_roc?.toFixed(3) || "N/A"}
            </p>
          </div>
          {expanded ? (
            <ChevronUp className="w-5 h-5 text-gray-600" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-600" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-gray-200 p-6 bg-gray-50">
          <TabSelector tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

          <div className="mt-6">
            {activeTab === "metrics" && (
              <div className="space-y-4">
                {/* Info button for metric explanations */}
                <div className="flex items-center justify-end">
                  <button
                    onClick={handleInfoClick}
                    className="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-800 transition-colors"
                    title="What do these metrics mean?"
                  >
                    {showInterpretation ? (
                      <><X className="w-4 h-4" /> Hide explanations</>
                    ) : (
                      <><Info className="w-4 h-4" /> What do these mean?</>
                    )}
                  </button>
                </div>

                {/* Metric explanation panel */}
                {showInterpretation && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 space-y-3">
                    <p className="text-sm font-semibold text-blue-900">
                      {model.model_name} — Metric Interpretations
                    </p>
                    <p className="text-xs text-blue-800">
                      These metrics describe a survey-defined diabetes-status proxy in the evaluated sample.
                      Positive and negative labels are not independently confirmed clinical diagnoses.
                      Historical report wording is preserved; F1 does not specify clinical error costs.
                    </p>
                    {interpretationData && interpretationData !== "__builtin__" ? (
                      // Show parsed interpretation file
                      <pre className="text-xs text-blue-800 whitespace-pre-wrap font-sans leading-relaxed">
                        {interpretationData}
                      </pre>
                    ) : (
                      // Show built-in explanations
                      Object.entries(METRIC_EXPLANATIONS).map(([metric, data]) => (
                        <div key={metric}>
                          <p className="text-sm font-medium text-blue-900">{data.title}</p>
                          <p className="text-sm text-blue-800 mt-0.5">{data.plain}</p>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {/* Metric cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
                  <MetricCard label="AUC-ROC" value={model?.auc_roc ?? 0} format="percentage" />
                  <MetricCard label="F1 Score" value={model?.f1 ?? 0} format="percentage" />
                  <MetricCard label="Precision" value={model?.precision ?? 0} format="percentage" />
                  <MetricCard label="Recall" value={model?.recall ?? 0} format="percentage" />
                  <MetricCard label="Accuracy" value={model?.accuracy ?? 0} format="percentage" />
                </div>
              </div>
            )}

            {activeTab === "shap" && (
              <div className="space-y-4">
                <p className="text-sm text-gray-600 mb-4">
                  Global SHAP summary for the underlying uncalibrated estimator, computed on the holdout dataset. It does not directly explain the full calibrated ensemble probabilities or the final High/Low labels:
                </p>
                {modelNameSafe ? (
                  <div className="bg-white rounded-lg p-4 border border-gray-200 flex justify-center">
                    <img
                      src={globalShapUrl}
                      alt={`${model.model_name} Global SHAP Summary`}
                      className="max-w-full h-auto max-h-[600px] object-contain"
                    />
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-600">
                    Global SHAP visualisation not available.
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}