import { MetricCard } from "@/components/ui/MetricCard";
import type { Obligation, RevenueAtRiskResponse } from "@/types/api";
import { formatCurrency } from "@/lib/utils";

interface OverviewMetricsProps {
  obligations: Obligation[];
  revenueAtRisk: RevenueAtRiskResponse;
}

export function OverviewMetrics({
  obligations,
  revenueAtRisk,
}: OverviewMetricsProps) {
  const total = obligations.length;
  const satisfied = obligations.filter((o) => o.status === "SATISFIED").length;
  const inRecovery = obligations.filter(
    (o) => o.status === "RECOVERY_ELIGIBLE"
  ).length;

  const totalAmount = obligations.reduce((sum, o) => sum + o.amount, 0);
  const satisfiedAmount = obligations.reduce(
    (sum, o) => sum + o.satisfied_amount,
    0
  );
  const recoveryRate =
    totalAmount > 0 ? (satisfiedAmount / totalAmount) * 100 : 0;

  return (
    <div className="metrics-grid">
      <MetricCard
        label="Total Outstanding"
        value={formatCurrency(revenueAtRisk.total_outstanding_inr)}
        sub={`${revenueAtRisk.data.length} obligation${revenueAtRisk.data.length !== 1 ? "s" : ""} at risk`}
        accent="warning"
      />
      <MetricCard
        label="Recovered Amount"
        value={formatCurrency(satisfiedAmount)}
        sub={`${satisfied} of ${total} obligations satisfied`}
        accent="success"
      />
      <MetricCard
        label="Recovery Rate"
        value={`${recoveryRate.toFixed(1)}%`}
        sub="by amount (INR)"
        accent={recoveryRate > 60 ? "success" : recoveryRate > 30 ? "warning" : "danger"}
      />
      <MetricCard
        label="In Recovery"
        value={inRecovery}
        sub="recovery-eligible obligations"
        accent="default"
      />
    </div>
  );
}
