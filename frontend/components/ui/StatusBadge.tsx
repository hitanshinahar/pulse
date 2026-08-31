import type { ObligationStatus } from "@/types/api";
import { statusLabel, cn } from "@/lib/utils";

const variantMap: Record<ObligationStatus, string> = {
  UNRESOLVED: "badge--unresolved",
  RECOVERY_ELIGIBLE: "badge--eligible",
  AMBIGUOUS: "badge--ambiguous",
  PARTIALLY_SATISFIED: "badge--partial",
  SATISFIED: "badge--satisfied",
  OVER_COLLECTED: "badge--over",
  ESCALATED: "badge--escalated",
  CLOSED: "badge--closed",
};

interface StatusBadgeProps {
  status: ObligationStatus;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <span className={cn("status-badge", variantMap[status], className)}>
      {statusLabel(status)}
    </span>
  );
}
