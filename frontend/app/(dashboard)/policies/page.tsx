import { fetchActivePolicy } from "@/lib/api";
import { formatCurrency, formatDuration } from "@/lib/utils";
import { EmptyState } from "@/components/ui/EmptyState";
import PolicyForm from "./PolicyForm";

export const dynamic = "force-dynamic";

export default async function PoliciesPage() {
    let policy = null;
    let error: string | null = null;
    try { policy = await fetchActivePolicy(); } catch (err) { error = err instanceof Error ? err.message : "Unable to load policy."; }
    return <div className="page-content animate-in">
        <div className="page-header"><h1 className="page-title">Policies</h1><p className="page-description">Controls that bound autonomous recovery actions.</p></div>
        {error && <div className="error-banner" role="alert">{error}</div>}
        {!policy ? <div className="table-container"><EmptyState title="No recovery policy found" description="Create a policy before evaluating recovery decisions." /></div> :
            <>
                <div className="metrics-grid" style={{ marginBottom: "var(--space-8)" }}>
                    <div className="metric-card"><span className="metric-card__label">Policy status</span><span className="metric-card__value">{policy.enabled ? "ENABLED" : "DISABLED"}</span><span className="metric-card__sub">Firewall control plane</span></div>
                    <div className="metric-card"><span className="metric-card__label">Autonomous limit</span><span className="metric-card__value">{formatCurrency(policy.max_autonomous_amount)}</span><span className="metric-card__sub">Maximum per action</span></div>
                    <div className="metric-card"><span className="metric-card__label">Cooldown</span><span className="metric-card__value">{formatDuration(policy.cooldown_seconds)}</span><span className="metric-card__sub">Between actions</span></div>
                </div>
                <PolicyForm initial={policy} />
            </>}
    </div>;
}
