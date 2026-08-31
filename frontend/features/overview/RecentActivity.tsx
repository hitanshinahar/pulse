import type { Obligation } from "@/types/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatCurrency, formatDate } from "@/lib/utils";

interface RecentActivityProps {
  obligations: Obligation[];
}

export function RecentActivity({ obligations }: RecentActivityProps) {
  const recent = obligations.slice(0, 10);

  if (recent.length === 0) {
    return (
      <div className="table-container">
        <EmptyState
          title="No obligations yet"
          description="Obligations will appear here once Razorpay webhook events are received."
        />
      </div>
    );
  }

  return (
    <div className="table-container">
      <table className="data-table" aria-label="Recent financial obligations">
        <thead>
          <tr>
            <th>Order ID</th>
            <th>Amount</th>
            <th>Outstanding</th>
            <th>Status</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          {recent.map((o) => (
            <tr key={o.id}>
              <td className="table-cell--mono">{o.razorpay_order_id}</td>
              <td style={{ color: "var(--text-primary)", fontWeight: 500 }}>
                {formatCurrency(o.amount, o.currency)}
              </td>
              <td>
                {o.outstanding_amount > 0 ? (
                  <span style={{ color: "var(--warning)" }}>
                    {formatCurrency(o.outstanding_amount, o.currency)}
                  </span>
                ) : (
                  <span style={{ color: "var(--success)" }}>—</span>
                )}
              </td>
              <td>
                <StatusBadge status={o.status} />
              </td>
              <td style={{ color: "var(--text-tertiary)", fontSize: "12px" }}>
                {formatDate(o.updated_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
