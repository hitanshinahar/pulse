import { fetchObligations, fetchRecoveryDecisions, fetchDecisionAudit } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/utils";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";

export const dynamic = "force-dynamic";

export default async function DecisionsPage() {
    let rows: Array<{ decision: Awaited<ReturnType<typeof fetchRecoveryDecisions>>[number]; obligationId: string; audit: Awaited<ReturnType<typeof fetchDecisionAudit>> | null }> = [];
    let error: string | null = null;
    try {
        const obligations = (await fetchObligations({ limit: 100 })).data;
        const groups = await Promise.all(obligations.map(async (obligation) => {
            const decisions = await fetchRecoveryDecisions(obligation.id);
            return Promise.all(decisions.map(async (decision) => ({
                decision,
                obligationId: obligation.id,
                audit: await fetchDecisionAudit(decision.id).catch(() => null),
            })));
        }));
        rows = groups.flat();
    } catch (err) {
        error = err instanceof Error ? err.message : "Unable to load decisions.";
    }

    return (
        <div className="page-content animate-in">
            <div className="page-header">
                <h1 className="page-title">Decisions</h1>
                <p className="page-description">Operational log of AI recommendations and firewall outcomes.</p>
            </div>
            {error && <div className="error-banner" role="alert">{error}</div>}
            <div className="section">
                <div className="section__header"><span className="section__title">Decision Log</span><span className="section__count">{rows.length}</span></div>
                <div className="table-container">
                    {rows.length === 0 ? <EmptyState title="No decisions found" description="Recovery decisions will appear here when generated." /> : (
                        <table className="data-table">
                            <thead><tr><th>Decision</th><th>Obligation</th><th>Action</th><th>Status</th><th>Incremental</th><th>Expected recovery</th><th>Created</th></tr></thead>
                            <tbody>{rows.map(({ decision, obligationId, audit }) => {
                                const evaluation = audit?.evaluations?.at(-1);
                                return <tr key={decision.id}>
                                    <td className="table-cell--mono">{decision.id.slice(0, 8)}…</td>
                                    <td className="table-cell--mono">{obligationId.slice(0, 8)}…</td>
                                    <td className="table-cell--primary">{decision.action}</td>
                                    <td><span className="status-badge">{decision.status}</span></td>
                                    <td>{decision.incremental_probability == null ? "—" : `${(decision.incremental_probability * 100).toFixed(1)}%`}</td>
                                    <td>{formatCurrency(decision.expected_incremental_amount ?? 0)}</td>
                                    <td>{formatDate(decision.created_at)}</td>
                                </tr>;
                            })}</tbody>
                        </table>
                    )}
                </div>
            </div>
            {rows.some((row) => row.audit) && <div className="section">
                <div className="section__header"><span className="section__title">Decision Lifecycle</span></div>
                {rows.filter((row) => row.audit).map(({ decision, audit }) => {
                    const evaluation = audit!.evaluations.at(-1);
                    return <details key={`audit-${decision.id}`} className="table-container" style={{ marginBottom: "var(--space-3)", padding: "var(--space-4)" }}>
                        <summary className="table-cell--primary" style={{ cursor: "pointer" }}>{decision.id.slice(0, 8)}… → {evaluation?.result ?? "Awaiting firewall"} → {audit!.executions[0]?.status ?? "No execution"}</summary>
                        <div style={{ marginTop: "var(--space-4)", display: "grid", gap: "8px" }}>
                            <div>Decision: {decision.action} ({decision.status})</div>
                            <div>Firewall: {evaluation ? `${evaluation.result} · ${evaluation.reason_code}` : "Not evaluated"}</div>
                            <div>State version: {evaluation ? `${evaluation.state_version_expected} expected / ${evaluation.state_version_actual} actual` : "—"}</div>
                            <div>Checks: {evaluation ? Object.entries(evaluation.checks).map(([key, value]) => `${key}: ${value ? "pass" : "fail"}`).join(" · ") : "—"}</div>
                            <div>Execution: {audit!.executions[0] ? `${audit!.executions[0].id} · ${audit!.executions[0].status}` : "Not created"}</div>
                        </div>
                    </details>;
                })}
            </div>}
        </div>
    );
}
