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
            ? "No data from this form is stored in the database. All predictions are processed temporarily and discarded immediately after generation."
            : "This is an exploratory tool for educational purposes only and does not replace clinical testing, professional medical diagnosis, or healthcare consultation. Always consult with a qualified healthcare provider for medical advice."}
        </p>
      </div>
    </div>
  );
}
