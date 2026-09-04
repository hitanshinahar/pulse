import { fetchObligations, fetchRecoveryDecisions, fetchDecisionAudit, fetchExecution } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { EmptyState } from "@/components/ui/EmptyState";
import ExecutionActions from "./ExecutionActions";

export const dynamic = "force-dynamic";

export default async function ExecutionsPage() {
    const executions: Awaited<ReturnType<typeof fetchExecution>>[] = [];
    let error: string | null = null;
    try {
        const obligations = (await fetchObligations({ limit: 100 })).data;
        const decisions = (await Promise.all(obligations.map((obligation) => fetchRecoveryDecisions(obligation.id).catch(() => [])))).flat();
        const audits = await Promise.all(decisions.map((decision) => fetchDecisionAudit(decision.id).catch(() => null)));
        const ids = audits.flatMap((audit) => audit?.executions.map((execution) => execution.id) ?? []);
        executions.push(...(await Promise.all(ids.map((id) => fetchExecution(id).catch(() => null)))).filter((execution): execution is Awaited<ReturnType<typeof fetchExecution>> => execution !== null));
    } catch (err) {
        error = err instanceof Error ? err.message : "Unable to load executions.";
    }
    return <div className="page-content animate-in">
        <div className="page-header"><h1 className="page-title">Executions</h1><p className="page-description">Track authorized recovery actions and payment-link outcomes.</p></div>
        {error && <div className="error-banner" role="alert">{error}</div>}
        <div className="section"><div className="section__header"><span className="section__title">Execution Operations</span><span className="section__count">{executions.length}</span></div>
            <div className="table-container execution-table-container">{executions.length === 0 ? <EmptyState title="No executions found" description="Firewall-authorized executions will appear here." /> :
                <table className="data-table execution-table"><thead><tr><th>Execution</th><th>Decision</th><th>Status</th><th>Razorpay reference</th><th>Payment link</th><th>Short URL</th><th>Executed</th><th>Operations</th></tr></thead>
                    <tbody>{executions.map((execution) => <tr key={execution.id}><td className="table-cell--mono">{execution.id.slice(0, 8)}…</td><td className="table-cell--mono">{execution.decision_id.slice(0, 8)}…</td><td><span className={`status-badge ${execution.status === "EXECUTED" ? "status-badge--success" : execution.status === "EXECUTION_FAILED" ? "status-badge--danger" : execution.status === "EXECUTION_UNKNOWN" ? "status-badge--danger" : "status-badge--warning"}`}>{execution.status}</span></td><td><span className="execution-table__truncate" title={execution.razorpay_reference_id ?? undefined}>{execution.razorpay_reference_id ?? "—"}</span></td><td><span className="execution-table__truncate" title={execution.razorpay_payment_link_id ?? undefined}>{execution.razorpay_payment_link_id ?? "—"}</span></td><td>{execution.short_url ? <a href={execution.short_url} target="_blank" rel="noreferrer" className="button button--secondary">Open Payment Link</a> : "—"}</td><td>{execution.executed_at ? formatDate(execution.executed_at) : "—"}</td><td>{execution.status === "EXECUTION_UNKNOWN" ? <ExecutionActions executionId={execution.id} /> : "—"}</td></tr>)}</tbody>
                </table>}
            </div>
        </div>
    </div>;
}
