interface MetricCardProps {
  label: string;
  value: number;
  format?: "percentage" | "decimal";
}

export function MetricCard({
  label,
  value,
  format = "decimal",
}: MetricCardProps) {
  const displayValue =
    format === "percentage"
      ? `${(value * 100).toFixed(1)}%`
      : value.toFixed(3);

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <p className="text-sm text-gray-600 font-medium">{label}</p>
      <p className="text-2xl font-bold text-gray-900 mt-2">{displayValue}</p>
    </div>
  );
}
