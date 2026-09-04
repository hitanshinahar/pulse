"use client";

import { useState } from "react";
import type { RecoveryPolicy } from "@/types/api";
import { savePolicy } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

export default function PolicyForm({ initial }: { initial: RecoveryPolicy }) {
    const [policy, setPolicy] = useState(initial);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState<string | null>(null);

    async function submit(event: React.FormEvent) {
        event.preventDefault();
        setSaving(true);
        setMessage(null);
        try {
            await savePolicy({
                max_autonomous_amount: policy.max_autonomous_amount,
                max_actions_per_obligation: policy.max_actions_per_obligation,
                cooldown_seconds: policy.cooldown_seconds,
                allowed_actions: policy.allowed_actions,
                require_human_above_amount: policy.require_human_above_amount,
                enabled: policy.enabled,
            });
            setMessage("Policy saved.");
        } catch (error) {
            setMessage(error instanceof Error ? error.message : "Unable to save policy.");
        } finally {
            setSaving(false);
        }
    }

    return <form onSubmit={submit} className="section">
        <div className="section__header"><span className="section__title">Policy Controls</span></div>
        <div style={{ display: "grid", gap: "var(--space-4)", maxWidth: "560px" }}>
            <label style={{ display: "grid", gap: "6px" }}><span className="policy-field__label">Maximum autonomous amount (INR)</span>
                <input className="input" type="number" min="0" value={policy.max_autonomous_amount} onChange={(event) => setPolicy({ ...policy, max_autonomous_amount: Number(event.target.value) })} />
            </label>
            <label style={{ display: "grid", gap: "6px" }}><span className="policy-field__label">Maximum actions per obligation</span>
                <input className="input" type="number" min="0" value={policy.max_actions_per_obligation} onChange={(event) => setPolicy({ ...policy, max_actions_per_obligation: Number(event.target.value) })} />
            </label>
            <label style={{ display: "grid", gap: "6px" }}><span className="policy-field__label">Cooldown (seconds)</span>
                <input className="input" type="number" min="0" value={policy.cooldown_seconds} onChange={(event) => setPolicy({ ...policy, cooldown_seconds: Number(event.target.value) })} />
            </label>
            <label style={{ display: "grid", gap: "6px" }}><span className="policy-field__label">Allowed actions</span>
                <input className="input" value={policy.allowed_actions.join(", ")} onChange={(event) => setPolicy({ ...policy, allowed_actions: event.target.value.split(",").map((value) => value.trim()).filter(Boolean) })} />
            </label>
            <label><input type="checkbox" checked={policy.enabled} onChange={(event) => setPolicy({ ...policy, enabled: event.target.checked })} /> Policy enabled</label>
            <label><input type="checkbox" checked={policy.require_human_above_amount} onChange={(event) => setPolicy({ ...policy, require_human_above_amount: event.target.checked })} /> Require human approval above limit</label>
            <div style={{ color: "var(--text-tertiary)", fontSize: "12px" }}>AI recommends. Policy controls what is allowed. Firewall enforces it.</div>
            <button className="button button--primary" disabled={saving}>{saving ? "Saving…" : "Save Policy"}</button>
            {message && <div role="status">{message}</div>}
        </div>
    </form>;
}
