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