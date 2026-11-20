import { AlertCircle } from "lucide-react";

interface DisclaimerBannerProps {
  variant?: "general" | "privacy";
}

export function DisclaimerBanner({ variant = "general" }: DisclaimerBannerProps) {
  const isPrivacy = variant === "privacy";

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex gap-3">
      <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
      <div>
        <p className="text-sm text-amber-900 font-medium">
          {isPrivacy ? "Data Privacy Notice" : "Important Disclaimer"}
        </p>
        <p className="text-sm text-amber-800 mt-1">
          {isPrivacy
            ? "Inputs are sent to the configured API for inference. The application does not intentionally save input payloads or predictions to a database. Form values and results remain in browser memory while displayed; hosting logs depend on the deployment."
            : "Educational research illustration using a survey-derived diabetes-status label, not a clinically validated Type 2 diabetes diagnosis or future-risk forecast. Predictions are not medical advice; consult a qualified healthcare professional."}
        </p>
      </div>
    </div>
  );
}
