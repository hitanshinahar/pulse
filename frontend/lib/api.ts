import type {
  ObligationsResponse,
  RevenueAtRiskResponse,
  RecoveryPolicy,
  RazorpayHealthResponse,
} from "@/types/api";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`;
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
      if (body?.detail) detail = String(body.detail);
    } catch {
      // ignore parse failure
    }
    throw new ApiError(res.status, detail);
  }

  return res.json() as Promise<T>;
}

// ─── Obligations ─────────────────────────────────────────────────────────────

export async function fetchObligations(
  opts: { status?: string; limit?: number; offset?: number } = {}
): Promise<ObligationsResponse> {
  const params = new URLSearchParams();
  if (opts.status) params.set("status", opts.status);
  if (opts.limit !== undefined) params.set("limit", String(opts.limit));
  if (opts.offset !== undefined) params.set("offset", String(opts.offset));
  const qs = params.toString();
  return apiFetch<ObligationsResponse>(`/obligations${qs ? `?${qs}` : ""}`);
}

// ─── Revenue at Risk ─────────────────────────────────────────────────────────

export async function fetchRevenueAtRisk(): Promise<RevenueAtRiskResponse> {
  return apiFetch<RevenueAtRiskResponse>("/revenue-at-risk");
}

// ─── Recovery Policy ─────────────────────────────────────────────────────────

export async function fetchActivePolicy(): Promise<RecoveryPolicy> {
  return apiFetch<RecoveryPolicy>("/api/v1/recovery/policy");
}

// ─── System Health ────────────────────────────────────────────────────────────

export async function fetchRazorpayHealth(): Promise<RazorpayHealthResponse> {
  return apiFetch<RazorpayHealthResponse>("/api/v1/health/razorpay");
}
