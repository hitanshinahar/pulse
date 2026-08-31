import { TopBar } from "@/components/shell/TopBar";
import { OverviewMetrics } from "@/features/overview/OverviewMetrics";
import { ObligationDistribution } from "@/features/overview/ObligationDistribution";
import { RecoveryFunnel } from "@/features/overview/RecoveryFunnel";
import { RecentActivity } from "@/features/overview/RecentActivity";
import { SystemHealth } from "@/features/overview/SystemHealth";
import {
  fetchObligations,
  fetchRevenueAtRisk,
  fetchActivePolicy,
  fetchRazorpayHealth,
} from "@/lib/api";
import type {
  ObligationsResponse,
  RevenueAtRiskResponse,
  RecoveryPolicy,
  RazorpayHealthResponse,
} from "@/types/api";

// Revalidate every 30 seconds — fresh data without full SSR on every request
export const revalidate = 30;

async function safefetch<T>(
  fn: () => Promise<T>,
  fallback: T
): Promise<{ data: T; error: string | null }> {
  try {
    const data = await fn();
    return { data, error: null };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return { data: fallback, error: message };
  }
}

export default async function OverviewPage() {
  // Fetch all data in parallel — failures are isolated, page still renders
  const [obligationsResult, revenueResult, policyResult, healthResult] =
    await Promise.all([
      safefetch<ObligationsResponse>(
        () => fetchObligations({ limit: 50 }),
        { data: [] }
      ),
      safefetch<RevenueAtRiskResponse>(
        () => fetchRevenueAtRisk(),
        { data: [], total_outstanding_inr: 0 }
      ),
      safefetch<RecoveryPolicy | null>(
        () => fetchActivePolicy(),
        null
      ),
      safefetch<RazorpayHealthResponse | null>(
        () => fetchRazorpayHealth(),
        null
      ),
    ]);

  const obligations = obligationsResult.data.data;
  const revenueAtRisk = revenueResult.data;
  const policy = policyResult.data;
  const razorpayHealth = healthResult.data;

  return (
    <>
      <TopBar page="Overview" />

      <div className="page-content animate-in">
        {/* Page header */}
        <div className="page-header">
          <h1 className="page-title">Overview</h1>
          <p className="page-description">
            Recovery performance and obligation state across all active obligations.
          </p>
        </div>

        {/* API error banner */}
        {obligationsResult.error && (
          <div className="error-banner" role="alert" style={{ marginBottom: "var(--space-6)" }}>
            Could not load obligations: {obligationsResult.error}
          </div>
        )}

        {/* Recovery metrics */}
        <div className="section">
          <div className="section__header">
            <span className="section__title">Recovery Performance</span>
          </div>
          <OverviewMetrics
            obligations={obligations}
            revenueAtRisk={revenueAtRisk}
          />
        </div>

        {/* Funnel */}
        <div className="section">
          <div className="section__header">
            <span className="section__title">Recovery Lifecycle</span>
          </div>
          <RecoveryFunnel />
        </div>

        {/* Two-column: Distribution + System Health */}
        <div className="two-col section">
          <div>
            <div className="section__header">
              <span className="section__title">Obligation State</span>
            </div>
            <ObligationDistribution obligations={obligations} />
          </div>
          <div>
            <div className="section__header">
              <span className="section__title">System Health</span>
            </div>
            <SystemHealth
              policy={policy}
              razorpayHealth={razorpayHealth}
              razorpayError={healthResult.error}
            />
          </div>
        </div>

        {/* Recent activity */}
        <div className="section">
          <div className="section__header">
            <span className="section__title">Recent Obligations</span>
          </div>
          <RecentActivity obligations={obligations} />
        </div>
      </div>
    </>
  );
}
