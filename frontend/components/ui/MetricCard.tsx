import { cn } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  value: string | number;
  sub?: string;
  accent?: "default" | "success" | "warning" | "danger";
  className?: string;
}

export function MetricCard({
  label,
  value,
  sub,
  accent = "default",
  className,
}: MetricCardProps) {
  const accentClass = {
    default: "metric-card--default",
    success: "metric-card--success",
    warning: "metric-card--warning",
    danger: "metric-card--danger",
  }[accent];

  return (
    <div className={cn("metric-card", accentClass, className)}>
      <p className="metric-card__label">{label}</p>
      <p className="metric-card__value">{value}</p>
      {sub && <p className="metric-card__sub">{sub}</p>}
    </div>
  );
}
