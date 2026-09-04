/**
 * API response types derived directly from backend schemas.
 * Field names match exact backend serialization — do not alter without checking backend code.
 */

// ─── /obligations ────────────────────────────────────────────────────────────

export type ObligationStatus =
  | "UNRESOLVED"
  | "RECOVERY_ELIGIBLE"
  | "AMBIGUOUS"
  | "PARTIALLY_SATISFIED"
  | "SATISFIED"
  | "OVER_COLLECTED"
  | "ESCALATED"
  | "CLOSED";

export interface Obligation {
  id: string;
  merchant_reference: string | null;
  razorpay_order_id: string;
  amount: number;
  currency: string;
  satisfied_amount: number;
  outstanding_amount: number;
  status: ObligationStatus;
  state_version: number;
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
}

export interface ObligationsResponse {
  data: Obligation[];
}

// ─── /revenue-at-risk ────────────────────────────────────────────────────────

export interface RevenueAtRiskItem {
  id: string;
  razorpay_order_id: string;
  outstanding_amount: number;
  currency: string;
  status: ObligationStatus;
}

export interface RevenueAtRiskResponse {
  data: RevenueAtRiskItem[];
  total_outstanding_inr: number;
}

// ─── /api/v1/recovery/policy ─────────────────────────────────────────────────

export interface RecoveryPolicy {
  id: string;
  max_autonomous_amount: number;
  max_actions_per_obligation: number;
  cooldown_seconds: number;
  allowed_actions: string[];
  require_human_above_amount: boolean;
  enabled: boolean;
}

// ─── /api/v1/health/razorpay ─────────────────────────────────────────────────

export interface RazorpayHealthResponse {
  status: string;   // "success" on healthy
  message: string;
}
export interface PaymentAttempt {
  id: string;
  razorpay_payment_id: string;
  amount: number;
  currency: string;
  payment_method: string | null;
  razorpay_status: string;
  created_at: string;
}

export interface ObligationStateTransition {
  id: string;
  previous_state: ObligationStatus | null;
  new_state: ObligationStatus;
  previous_version: number;
  new_version: number;
  reason: string | null;
  source: string | null;
  triggering_event_id: string | null;
  created_at: string;
}

export interface ObligationTimelineResponse {
  payment_attempts: PaymentAttempt[];
  state_transitions: ObligationStateTransition[];
}

// ─── Recovery ────────────────────────────────────────────────────────────────

export interface RecoveryPrediction {
  obligation_id: string;
  candidate_action: string;
  probability: number;
  model_version: string;
  feature_schema_version: number;
}

export interface RecoveryFeatureSnapshot {
  id: string;
  obligation_id: string;
  feature_schema_version: number;
  features: Record<string, unknown>;
  created_at: string;
}

export interface RecoveryDecisionSummary {
  id: string;
  action: string;
  status: string;
  incremental_probability: number;
  expected_incremental_amount: number;
  created_at: string;
}

export interface FirewallEvaluationResponse {
  decision_id: string;
  result: "ALLOW" | "BLOCK" | "EXPIRE";
  reason_code: string;
  reason: string;
  checks: Record<string, boolean>;
  state_version_expected: number;
  state_version_actual: number;
}

export interface DecisionAudit {
  decision: {
    id: string;
    obligation_id: string;
    state_version: number;
    action: string;
    status: string;
    created_at: string;
  };
  evaluations: Array<{
    result: string;
    reason_code: string;
    checks: Record<string, boolean>;
    created_at: string;
  }>;
  executions: Array<{
    status: string;
    idempotency_key: string;
    executed_at: string | null;
  }>;
}

export interface RecoveryExecutionResponse {
  id: string;
  status: string;
  razorpay_reference_id: string | null;
  razorpay_payment_link_id: string | null;
  short_url: string | null;
}

// ─── Recovery ────────────────────────────────────────────────────────────────

export interface RecoveryDecision {
  id: string;
  obligation_id?: string;
  action: string;
  status: string;
  baseline_probability?: number | null;
  action_probability?: number | null;
  incremental_probability: number | null;
  expected_incremental_amount: number | null;
  state_version?: number;
  model_version?: string | null;
  llm_diagnosis?: string | null;
  created_at?: string;
}

export interface RecoveryDecisionListItem {
  id: string;
  action: string;
  status: string;
  incremental_probability: number | null;
  expected_incremental_amount: number | null;
  created_at: string;
}

export interface FirewallEvaluation {
  result: "ALLOW" | "BLOCK" | "EXPIRE";
  reason_code: string;
  reason: string;
  checks: Record<string, boolean>;
  state_version_expected: number;
  state_version_actual: number;
}

export interface RecoveryEvaluationResponse {
  decision_id: string;
  result: "ALLOW" | "BLOCK" | "EXPIRE";
  reason_code: string;
  reason: string;
  checks: Record<string, boolean>;
  state_version_expected: number;
  state_version_actual: number;
}

export interface RecoveryExecution {
  id: string;
  decision_id: string;
  status: string;
  razorpay_reference_id: string | null;
  razorpay_payment_link_id: string | null;
  short_url: string | null;
  executed_at: string | null;
}

export interface RecoveryDecisionAudit {
  decision: {
    id: string;
    obligation_id: string;
    state_version: number;
    action: string;
    status: string;
    created_at: string;
  };
  evaluations: FirewallEvaluation[];
  executions: {
    id: string;
    status: string;
    idempotency_key: string;
    executed_at: string | null;
  }[]
}

export interface RazorpayEvent {
  id: string;
  razorpay_event_id: string;
  event_type: string;
  parsed_payload: Record<string, unknown>;
  status: string;
  created_at: string;
  processed_at: string | null;
  error_msg: string | null;
}

export interface RazorpayEventsResponse {
  events: RazorpayEvent[];
}
