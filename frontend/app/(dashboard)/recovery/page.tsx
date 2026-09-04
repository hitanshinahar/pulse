import {
    fetchObligations,
    fetchRecoveryDecisions,
} from "@/lib/api";

import type { RecoveryDecisionListItem } from "@/types/api";

import { formatCurrency, formatDate } from "@/lib/utils";
import RecoveryCandidate from "@/components/recovery/RecoveryCandidate";
import { StatusBadge } from "@/components/ui/StatusBadge";

export const dynamic = "force-dynamic";

async function getCandidateDecisions(obligationId: string) {
    try {
        return await fetchRecoveryDecisions(obligationId);
    } catch {
        return [];
    }
}
export default async function RecoveryPage() {
    const obligationsResponse = await fetchObligations({ limit: 50 });

    const obligations = obligationsResponse.data;

    const eligible = obligations.filter(
        (obligation) =>
            obligation.status === "RECOVERY_ELIGIBLE" ||
            obligation.status === "PARTIALLY_SATISFIED"
    );

    const satisfied = obligations.filter(
        (obligation) => obligation.status === "SATISFIED"
    );

    const outstanding = obligations.reduce(
        (sum, obligation) => sum + obligation.outstanding_amount,
        0
    );

    return (
        <div className="page-content animate-in">
            {/* Header */}
            <div className="page-header">
                <div>
                    <div className="detail-header__eyebrow">
                        RECOVERY CONTROL
                    </div>

                    <h1 className="page-title">Recovery</h1>

                    <p className="page-description">
                        Intelligent recovery decisions, firewall authorization, and
                        execution state.
                    </p>
                </div>
            </div>

            {/* Overview */}
            <section className="section">
                <div className="section__header">
                    <span className="section__title">
                        Recovery Overview
                    </span>
                </div>

                <div className="recovery-overview-grid">
                    <div className="recovery-stat">
                        <span className="recovery-stat__label">
                            Eligible
                        </span>

                        <span className="recovery-stat__value">
                            {eligible.length}
                        </span>

                        <span className="recovery-stat__sub">
                            obligations requiring recovery
                        </span>
                    </div>

                    <div className="recovery-stat">
                        <span className="recovery-stat__label">
                            Outstanding
                        </span>

                        <span className="recovery-stat__value">
                            {formatCurrency(outstanding, "INR")}
                        </span>

                        <span className="recovery-stat__sub">
                            revenue currently at risk
                        </span>
                    </div>

                    <div className="recovery-stat">
                        <span className="recovery-stat__label">
                            Recovered
                        </span>

                        <span className="recovery-stat__value recovery-stat__value--success">
                            {satisfied.length}
                        </span>

                        <span className="recovery-stat__sub">
                            satisfied obligations
                        </span>
                    </div>

                    <div className="recovery-stat">
                        <span className="recovery-stat__label">
                            Recovery Engine
                        </span>

                        <span className="recovery-stat__value recovery-stat__value--success">
                            ACTIVE
                        </span>

                        <span className="recovery-stat__sub">
                            decision + firewall pipeline
                        </span>
                    </div>
                </div>
            </section>

            {/* Lifecycle */}
            <section className="section">
                <div className="section__header">
                    <span className="section__title">
                        Recovery Lifecycle
                    </span>
                </div>

                <div className="recovery-lifecycle">
                    {[
                        ["01", "Obligation", "Financial state"],
                        ["02", "Prediction", "Recovery probability"],
                        ["03", "Decision", "Candidate action"],
                        ["04", "Firewall", "Policy authorization"],
                        ["05", "Execution", "External action"],
                    ].map(([number, title, subtitle], index, items) => (
                        <div className="recovery-lifecycle__item" key={title}>
                            <div className="recovery-lifecycle__node">
                                <span className="recovery-lifecycle__number">
                                    {number}
                                </span>

                                <span className="recovery-lifecycle__title">
                                    {title}
                                </span>

                                <span className="recovery-lifecycle__subtitle">
                                    {subtitle}
                                </span>
                            </div>

                            {index < items.length - 1 && (
                                <span className="recovery-lifecycle__arrow">
                                    →
                                </span>
                            )}
                        </div>
                    ))}
                </div>
            </section>

            {/* Eligible obligations */}
            <section className="section">
                <div className="section__header">
                    <span className="section__title">
                        Recovery Candidates
                    </span>

                    <span className="section__count">
                        {eligible.length}
                    </span>
                </div>

                {eligible.length === 0 ? (
                    <div className="empty-detail">
                        <div className="empty-detail__icon">○</div>

                        <p>No recovery candidates.</p>

                        <span>
                            Obligations eligible for recovery will appear here.
                        </span>
                    </div>
                ) : (
                    <div className="recovery-candidate-list">
                        {(
                            await Promise.all(
                                eligible.map(async (obligation) => {
                                    let decisions: RecoveryDecisionListItem[] = [];

                                    try {
                                        decisions = await fetchRecoveryDecisions(
                                            obligation.id
                                        );
                                    } catch {
                                        decisions = [];
                                    }

                                    return {
                                        obligation,
                                        decisions,
                                    };
                                })
                            )
                        ).map(({ obligation, decisions }) => (
                            <RecoveryCandidate
                                key={obligation.id}
                                obligation={obligation}
                                initialDecisions={decisions}
                            />
                        ))}
                    </div>
                )}
            </section>
        </div>
    );
}