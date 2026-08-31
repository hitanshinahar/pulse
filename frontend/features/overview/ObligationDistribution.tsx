import type { Obligation, ObligationStatus } from "@/types/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatCurrency } from "@/lib/utils";

const STATUS_ORDER: ObligationStatus[] = [
  "RECOVERY_ELIGIBLE",
  "UNRESOLVED",
  "PARTIALLY_SATISFIED",
  "AMBIGUOUS",
  "SATISFIED",
  "ESCALATED",
  "OVER_COLLECTED",
  "CLOSED",
];

interface ObligationDistributionProps {
  obligations: Obligation[];
}

export function ObligationDistribution({
  obligations,
}: ObligationDistributionProps) {
  // Build counts + amounts per status
  const groups = STATUS_ORDER.map((status) => {
    const items = obligations.filter((o) => o.status === status);
    const outstanding = items.reduce((s, o) => s + o.outstanding_amount, 0);
    return { status, count: items.length, outstanding };
  }).filter((g) => g.count > 0);

  if (groups.length === 0) {
    return (
      <p style={{ fontSize: "13px", color: "var(--text-tertiary)" }}>
        No obligations recorded.
      </p>
    );
  }

  return (
    <div className="dist-grid">
      {groups.map(({ status, count, outstanding }) => (
        <div key={status} className="dist-item">
          <StatusBadge status={status} />
          <span className="dist-item__count">{count}</span>
          {outstanding > 0 && (
            <span className="dist-item__amount">
              {formatCurrency(outstanding)} outstanding
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
