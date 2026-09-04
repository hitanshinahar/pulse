import { fetchRazorpayEvents } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { EmptyState } from "@/components/ui/EmptyState";

export const dynamic = "force-dynamic";

export default async function EventsPage() {
    let events: Awaited<ReturnType<typeof fetchRazorpayEvents>>["events"] = [];
    let error: string | null = null;
    try { events = (await fetchRazorpayEvents()).events; } catch (err) { error = err instanceof Error ? err.message : "Unable to load events."; }
    return <div className="page-content animate-in">
        <div className="page-header"><h1 className="page-title">Events</h1><p className="page-description">Razorpay payment lifecycle events processed by Pulse.</p></div>
        {error && <div className="error-banner" role="alert">{error}</div>}
        <div className="section"><div className="section__header"><span className="section__title">Webhook Operations</span><span className="section__count">{events.length}</span></div>
            <div className="table-container">{events.length === 0 ? <EmptyState title="No webhook events found" description="Events will appear here when Razorpay webhooks are received." /> :
                <table className="data-table"><thead><tr><th>Event</th><th>Type</th><th>Status</th><th>Payment / order</th><th>Received</th><th>Processed</th></tr></thead><tbody>{events.map((event) => {
                    const payload = event.parsed_payload;
                    const paymentId = typeof payload.payment_id === "string" ? payload.payment_id : typeof payload.id === "string" ? payload.id : "—";
                    return <tr key={event.id}><td className="table-cell--mono">{event.razorpay_event_id}</td><td className="table-cell--primary">{event.event_type}</td><td><span className="status-badge">{event.status}</span></td><td className="table-cell--mono">{paymentId}</td><td>{formatDate(event.created_at)}</td><td>{event.processed_at ? formatDate(event.processed_at) : "—"}</td></tr>;
                })}</tbody></table>}
            </div>
        </div>
    </div>;
}
