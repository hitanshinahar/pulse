"use client";

import { useState } from "react";

export default function ExecutionActions({
    executionId,
}: {
    executionId: string;
}) {
    const [status, setStatus] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    async function reconcile() {
        setLoading(true);
        setStatus(null);
        try {
            const response = await fetch(
                `/api/recovery/execution/${executionId}/reconcile`,
                { method: "POST" }
            );
            const data = (await response.json()) as { status?: string; detail?: string };
            if (!response.ok) throw new Error(data.detail || "Unable to reconcile execution.");
            setStatus(data.status || "Updated");
        } catch (error) {
            setStatus(error instanceof Error ? error.message : "Unable to reconcile execution.");
        } finally {
            setLoading(false);
        }
    }

    return <div>
        <button className="button button--secondary" onClick={reconcile} disabled={loading}>
            {loading ? "Reconciling…" : "Reconcile"}
        </button>
        {status && <div style={{ marginTop: "4px", fontSize: "11px" }}>{status}</div>}
    </div>;
}
