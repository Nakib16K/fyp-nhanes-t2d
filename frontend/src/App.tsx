import { useState, useEffect } from "react";
import { ModelComparisonMode } from "./components/ModelComparison/ModelComparisonMode";
import { ExploratoryMode } from "./components/Exploratory/ExploratoryMode";
import { LoadingSpinner } from "./components/LoadingSpinner";
import { api } from "./utils/api";

type Mode = "comparison" | "exploratory";

function App() {
  const [mode, setMode] = useState<Mode>("comparison");
  const [apiReady, setApiReady] = useState(false);
  const [apiError, setApiError] = useState(false);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        await api.healthCheck();
        setApiReady(true);
      } catch {
        setApiError(true);
      }
    };

    checkHealth();
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Title */}
            <h1 className="text-xl font-bold text-gray-900">
              Diabetes Prediction Dashboard
            </h1>

            <div className="flex gap-2">
              <button
                onClick={() => setMode("comparison")}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  mode === "comparison"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-900 hover:bg-gray-200"
                }`}
              >
                Model Comparison
              </button>
              <button
                onClick={() => setMode("exploratory")}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  mode === "exploratory"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-900 hover:bg-gray-200"
                }`}
              >
                Exploratory Mode
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {!apiReady && !apiError && (
          <div className="flex items-center justify-center py-12">
            <div className="space-y-4 text-center">
              <LoadingSpinner />
              <p className="text-gray-600">Connecting to API...</p>
            </div>
          </div>
        )}

        {apiError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
            <p className="text-red-900 font-medium">
              Unable to connect to API server
            </p>
            <p className="text-red-700 text-sm mt-2">
              Make sure the backend server is running on port 8000
            </p>
          </div>
        )}

        {apiReady && (
          <>
            {mode === "comparison" && <ModelComparisonMode />}
            {mode === "exploratory" && <ExploratoryMode />}
          </>
        )}
      </main>

      <footer className="bg-white border-t border-gray-200 mt-16 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-gray-600">
            This dashboard is for exploratory and educational purposes. Always consult
            with healthcare professionals for medical advice.
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;