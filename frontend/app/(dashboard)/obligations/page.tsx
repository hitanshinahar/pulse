import Link from "next/link";
import { fetchObligations } from "@/lib/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { Obligation, ObligationStatus } from "@/types/api";

export const revalidate = 15;

const statusFilters: {
    value: ObligationStatus | "";
    label: string;
}[] = [
        { value: "", label: "All obligations" },
        { value: "UNRESOLVED", label: "Unresolved" },
        { value: "RECOVERY_ELIGIBLE", label: "Recovery eligible" },
        { value: "AMBIGUOUS", label: "Ambiguous" },
        { value: "PARTIALLY_SATISFIED", label: "Partially satisfied" },
        { value: "SATISFIED", label: "Satisfied" },
        { value: "ESCALATED", label: "Escalated" },
        { value: "CLOSED", label: "Closed" },
    ];

interface ObligationsPageProps {
    searchParams: Promise<{
        status?: string;
    }>;
}

export default async function ObligationsPage({
    searchParams,
}: ObligationsPageProps) {
    const params = await searchParams;

    const status = statusFilters.some(
        (filter) => filter.value === params.status
    )
        ? (params.status as ObligationStatus)
        : undefined;

    let obligations: Obligation[] = [];
    let error: string | null = null;

    try {
        const response = await fetchObligations({
            status,
            limit: 100,
        });

        obligations = response.data;
    } catch (err) {
        error = err instanceof Error ? err.message : "Unable to load obligations.";
    }

    const totalOutstanding = obligations.reduce(
        (sum, obligation) => sum + obligation.outstanding_amount,
        0
    );

    const recoveryEligible = obligations.filter(
        (obligation) => obligation.status === "RECOVERY_ELIGIBLE"
    ).length;

    const satisfied = obligations.filter(
        (obligation) => obligation.status === "SATISFIED"
    ).length;

    return (
        <div className="page-content animate-in">
            {/* Page header */}
            <div className="page-header">
                <h1 className="page-title">Obligations</h1>
                <p className="page-description">
                    Monitor financial obligations and recovery state.
                </p>
            </div>

            {/* API error */}
            {error && (
                <div
                    className="error-banner"
                    role="alert"
                    style={{ marginBottom: "var(--space-6)" }}
                >
                    Could not load obligations: {error}
                </div>
            )}

            {/* Summary metrics */}
            <div
                className="metrics-grid"
                style={{ marginBottom: "var(--space-8)" }}
            >
                <div className="metric-card">
                    <span className="metric-card__label">Total obligations</span>
                    <span className="metric-card__value">{obligations.length}</span>
                    <span className="metric-card__sub">Current view</span>
                </div>

                <div className="metric-card metric-card--warning">
                    <span className="metric-card__label">Outstanding</span>
                    <span className="metric-card__value">
                        {formatCurrency(totalOutstanding)}
                    </span>
                    <span className="metric-card__sub">Amount still at risk</span>
                </div>

                <div className="metric-card">
                    <span className="metric-card__label">Recovery eligible</span>
                    <span className="metric-card__value">{recoveryEligible}</span>
                    <span className="metric-card__sub">
                        Awaiting recovery action
                    </span>
                </div>

                <div className="metric-card metric-card--success">
                    <span className="metric-card__label">Satisfied</span>
                    <span className="metric-card__value">{satisfied}</span>
                    <span className="metric-card__sub">Fully recovered</span>
                </div>
            </div>

            {/* Status filters */}
            <div className="section">
                <div
                    style={{
                        display: "flex",
                        gap: "8px",
                        flexWrap: "wrap",
                        marginBottom: "var(--space-4)",
                    }}
                >
                    {statusFilters.map((filter) => {
                        const active = filter.value === (status ?? "");

                        return (
                            <Link
                                key={filter.value || "all"}
                                href={
                                    filter.value
                                        ? `/obligations?status=${filter.value}`
                                        : "/obligations"
                                }
                                className={`filter-chip${active ? " filter-chip--active" : ""
                                    }`}
                            >
                                {filter.label}
                            </Link>
                        );
                    })}
                </div>

                {/* Empty state */}
                {obligations.length === 0 ? (
                    <div className="table-container">
                        <EmptyState
                            title="No obligations found"
                            description={
                                status
                                    ? `There are no ${status
                                        .toLowerCase()
                                        .replaceAll("_", " ")} obligations.`
                                    : "Obligations will appear here once Razorpay webhook events are received."
                            }
                        />
                    </div>
                ) : (
                    /* Obligations table */
                    <div className="table-container">
                        <table
                            className="data-table"
                            aria-label="Financial obligations"
                        >
                            <thead>
                                <tr>
                                    <th>Order ID</th>
                                    <th>Amount</th>
                                    <th>Satisfied</th>
                                    <th>Outstanding</th>
                                    <th>Status</th>
                                    <th>Updated</th>
                                </tr>
                            </thead>

                            <tbody>
                                {obligations.map((obligation) => (
                                    <tr key={obligation.id}>
                                        <td>
                                            <Link
                                                href={`/obligations/${obligation.id}`}
                                                className="table-link"
                                            >
                                                {obligation.razorpay_order_id}
                                            </Link>
                                        </td>

                                        <td
                                            style={{
                                                color: "var(--text-primary)",
                                                fontWeight: 500,
                                            }}
                                        >
                                            {formatCurrency(
                                                obligation.amount,
                                                obligation.currency
                                            )}
                                        </td>

                                        <td>
                                            {formatCurrency(
                                                obligation.satisfied_amount,
                                                obligation.currency
                                            )}
                                        </td>

                                        <td>
                                            {obligation.outstanding_amount > 0 ? (
                                                <span style={{ color: "var(--warning)" }}>
                                                    {formatCurrency(
                                                        obligation.outstanding_amount,
                                                        obligation.currency
                                                    )}
                                                </span>
                                            ) : (
                                                <span style={{ color: "var(--success)" }}>—</span>
                                            )}
                                        </td>

                                        <td>
                                            <StatusBadge status={obligation.status} />
                                        </td>

                                        <td
                                            style={{
                                                color: "var(--text-tertiary)",
                                                fontSize: "12px",
                                            }}
                                        >
                                            {formatDate(obligation.updated_at)}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}