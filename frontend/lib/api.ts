import type {
  Obligation,
  ObligationTimelineResponse,
  ObligationsResponse,
  RevenueAtRiskResponse,
  RecoveryPolicy,
  RazorpayHealthResponse,
  RecoveryFeatureSnapshot,
  RecoveryPrediction,
  RecoveryDecision,
  RecoveryDecisionListItem,
  RecoveryEvaluationResponse,
  RecoveryDecisionAudit,
  RecoveryExecution,
  RazorpayEventsResponse,
} from "@/types/api";

const BASE_URL =
  process.env.BACKEND_URL ||
  "http://localhost:8000";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(
  path: string,
  init?: RequestInit,
  options?: { useProxy?: boolean }
): Promise<T> {
  const url = options?.useProxy ? path : `${BASE_URL}${path}`;

  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!res.ok) {
    let detail = res.statusText;

    try {
      const body = await res.json();

      if (body?.detail) {
        detail = String(body.detail);
      }
    } catch {
      // Ignore parse failure.
    }

    throw new ApiError(res.status, detail);
  }

  return res.json() as Promise<T>;
}

// ─── Obligations ─────────────────────────────────────────────────────────────

export async function fetchObligations(
  opts: {
    status?: string;
    limit?: number;
    offset?: number;
  } = {}
): Promise<ObligationsResponse> {
  const params = new URLSearchParams();

  if (opts.status) {
    params.set("status", opts.status);
  }

  if (opts.limit !== undefined) {
    params.set("limit", String(opts.limit));
  }

  if (opts.offset !== undefined) {
    params.set("offset", String(opts.offset));
  }

  const qs = params.toString();

  return apiFetch<ObligationsResponse>(
    `/obligations${qs ? `?${qs}` : ""}`
  );
}

export async function fetchObligation(
  obligationId: string
): Promise<Obligation> {
  return apiFetch<Obligation>(
    `/obligations/${obligationId}`
  );
}

export async function fetchObligationTimeline(
  obligationId: string
): Promise<ObligationTimelineResponse> {
  return apiFetch<ObligationTimelineResponse>(
    `/obligations/${obligationId}/timeline`
  );
}

// ─── Revenue at Risk ──────────────────────────────────────────────────────────

export async function fetchRevenueAtRisk(): Promise<RevenueAtRiskResponse> {
  return apiFetch<RevenueAtRiskResponse>(
    "/revenue-at-risk"
  );
}

// ─── Recovery Policy ──────────────────────────────────────────────────────────

export async function fetchActivePolicy(): Promise<RecoveryPolicy> {
  return apiFetch<RecoveryPolicy>(
    "/api/v1/recovery/policy"
  );
}

export async function savePolicy(
  policy: Omit<RecoveryPolicy, "id">
): Promise<{ status: string; policy_id: string }> {
  return apiFetch<{ status: string; policy_id: string }>(
    "/api/recovery/policy",
    {
      method: "POST",
      body: JSON.stringify(policy),
    },
    { useProxy: true }
  );
}

export async function fetchRazorpayEvents(): Promise<RazorpayEventsResponse> {
  return apiFetch<RazorpayEventsResponse>("/api/v1/events/razorpay");
}

// ─── System Health ────────────────────────────────────────────────────────────

export async function fetchRazorpayHealth(): Promise<RazorpayHealthResponse> {
  return apiFetch<RazorpayHealthResponse>(
    "/api/v1/health/razorpay"
  );
}

// ─── Recovery Intelligence ───────────────────────────────────────────────────

export async function fetchRecoveryFeatures(
  obligationId: string
): Promise<RecoveryFeatureSnapshot> {
  return apiFetch<RecoveryFeatureSnapshot>(
    `/api/v1/recovery/features/${obligationId}`
  );
}

export async function fetchRecoveryPrediction(
  obligationId: string,
  candidateAction = "PAYMENT_LINK"
): Promise<RecoveryPrediction> {
  return apiFetch<RecoveryPrediction>(
    `/api/v1/recovery/prediction/${obligationId}?candidate_action=${encodeURIComponent(candidateAction)}`
  );
}

// ─── Recovery ────────────────────────────────────────────────────────────────

export async function fetchRecoveryDecisions(
  obligationId: string
): Promise<RecoveryDecisionListItem[]> {
  return apiFetch<RecoveryDecisionListItem[]>(
    typeof window === "undefined"
      ? `/api/v1/recovery/decisions/${obligationId}`
      : `/api/recovery/decisions/${obligationId}`,
    undefined,
    typeof window === "undefined" ? undefined : { useProxy: true }
  );
}

export async function createRecoveryDecision(
  obligationId: string
): Promise<RecoveryDecision> {
  return apiFetch<RecoveryDecision>(
    `/api/recovery/decision/${obligationId}`,
    {
      method: "POST",
    },
    { useProxy: true }
  );
}

export async function evaluateRecoveryDecision(
  decisionId: string
): Promise<RecoveryEvaluationResponse> {
  return apiFetch<RecoveryEvaluationResponse>(
    `/api/recovery/evaluate/${decisionId}`,
    {
      method: "POST",
    },
    { useProxy: true }
  );
}

export async function fetchDecisionAudit(
  decisionId: string
): Promise<RecoveryDecisionAudit> {
  return apiFetch<RecoveryDecisionAudit>(
    `/api/v1/recovery/decisions/${decisionId}/audit`
  );
}

export async function fetchExecution(
  executionId: string
): Promise<RecoveryExecution> {
  return apiFetch<RecoveryExecution>(
    `/api/v1/recovery/executions/${executionId}`
  );
}

export async function executeRecovery(
  executionId: string
): Promise<RecoveryExecution> {
  return apiFetch<RecoveryExecution>(
    `/api/v1/recovery/executions/${executionId}/execute`,
    {
      method: "POST",
    }
  );
}