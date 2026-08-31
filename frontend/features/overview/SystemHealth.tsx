import type { RecoveryPolicy, RazorpayHealthResponse } from "@/types/api";

interface SystemHealthProps {
  policy: RecoveryPolicy | null;
  razorpayHealth: RazorpayHealthResponse | null;
  razorpayError: string | null;
}

export function SystemHealth({
  policy,
  razorpayHealth,
  razorpayError,
}: SystemHealthProps) {
  const razorpayOk = razorpayHealth?.status === "success";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
      {/* Razorpay */}
      <div className="health-row">
        <span className="health-label">Razorpay Test Mode</span>
        <span className={`health-status health-status--${razorpayOk ? "ok" : "error"}`}>
          <span className={`health-dot health-dot--${razorpayOk ? "ok" : "error"}`} aria-hidden="true" />
          {razorpayOk
            ? "Connected"
            : razorpayError
            ? `Error: ${razorpayError}`
            : "Unavailable"}
        </span>
      </div>

      {/* Recovery Policy */}
      <div className="health-row">
        <span className="health-label">Recovery Policy</span>
        <span
          className={`health-status health-status--${policy ? (policy.enabled ? "ok" : "error") : "error"}`}
        >
          <span
            className={`health-dot health-dot--${policy ? (policy.enabled ? "ok" : "error") : "error"}`}
            aria-hidden="true"
          />
          {policy
            ? policy.enabled
              ? `Active · max ${policy.max_actions_per_obligation} actions/obligation`
              : "Disabled"
            : "No policy configured"}
        </span>
      </div>

      {/* Policy detail row */}
      {policy && (
        <div className="health-row">
          <span className="health-label">Autonomous Limit</span>
          <span style={{ fontSize: "12px", color: "var(--text-secondary)", fontFamily: "var(--font-mono)" }}>
            ₹{policy.max_autonomous_amount.toLocaleString("en-IN")}
            {policy.require_human_above_amount && " · human approval above"}
          </span>
        </div>
      )}
    </div>
  );
}
