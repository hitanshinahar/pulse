"use client";

import { useState } from "react";
import type {
    Obligation,
    RecoveryPrediction,
    RecoveryDecision,
    FirewallEvaluationResponse,
} from "@/types/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatCurrency } from "@/lib/utils";

interface RecoveryCandidate extends Obligation {
    prediction: RecoveryPrediction | null;
}

interface RecoveryCandidatesProps {
    candidates: RecoveryCandidate[];
}

interface EvaluationState {
    loading: boolean;
    decision: RecoveryDecision | null;
    firewall: FirewallEvaluationResponse | null;
    error: string | null;
}

export function RecoveryCandidates({
    candidates,
}: RecoveryCandidatesProps) {
    const [evaluations, setEvaluations] = useState<
        Record<string, EvaluationState>
    >({});

    async function evaluate(obligationId: string) {
        setEvaluations((current) => ({
            ...current,
            [obligationId]: {
                loading: true,
                decision: null,
                firewall: null,
                error: null,
            },
        }));

        try {
            const decisionResponse = await fetch(
                `/api/recovery/decision/${obligationId}`,
                {
                    method: "POST",
                }
            );

            if (!decisionResponse.ok) {
                const body = await decisionResponse.json().catch(() => null);
                throw new Error(
                    body?.detail || "Failed to create recovery decision"
                );
            }

            const decision: RecoveryDecision =
                await decisionResponse.json();

            const firewallResponse = await fetch(
                `/api/recovery/decision/${decision.id}/evaluate`,
                {
                    method: "POST",
                }
            );

            if (!firewallResponse.ok) {
                const body = await firewallResponse.json().catch(() => null);
                throw new Error(
                    body?.detail || "Failed to evaluate recovery decision"
                );
            }

            const firewall: FirewallEvaluationResponse =
                await firewallResponse.json();

            setEvaluations((current) => ({
                ...current,
                [obligationId]: {
                    loading: false,
                    decision,
                    firewall,
                    error: null,
                },
            }));
        } catch (error) {
            setEvaluations((current) => ({
                ...current,
                [obligationId]: {
                    loading: false,
                    decision: null,
                    firewall: null,
                    error:
                        error instanceof Error
                            ? error.message
                            : "Something went wrong",
                },
            }));
        }
    }

    if (candidates.length === 0) {
        return (
            <div className="empty-detail">
                <div className="empty-detail__icon">✓</div>
                <p>No obligations currently require recovery.</p>
                <span>
                    Recovery candidates will appear when an obligation becomes
                    eligible.
                </span>
            </div>
        );
    }

    return (
        <div className="recovery-candidates">
            {candidates.map((obligation) => {
                const state = evaluations[obligation.id];
                const probability = obligation.prediction?.probability ?? 0;

                return (
                    <div className="recovery-candidate" key={obligation.id}>
                        <div className="recovery-candidate__header">
                            <div>
                                <div className="recovery-candidate__eyebrow">
                                    FINANCIAL OBLIGATION
                                </div>

                                <div className="recovery-candidate__title-row">
                                    <h3 className="recovery-candidate__title">
                                        {obligation.razorpay_order_id}
                                    </h3>

                                    <StatusBadge status={obligation.status} />
                                </div>

                                {obligation.merchant_reference && (
                                    <p className="recovery-candidate__reference">
                                        {obligation.merchant_reference}
                                    </p>
                                )}
                            </div>

                            <div className="recovery-candidate__amount">
                                <span>Outstanding</span>
                                <strong>
                                    {formatCurrency(
                                        obligation.outstanding_amount,
                                        obligation.currency
                                    )}
                                </strong>
                            </div>
                        </div>

                        <div className="recovery-candidate__stats">
                            <div>
                                <span className="recovery-candidate__stat-label">
                                    Recovery probability
                                </span>

                                <span className="recovery-candidate__probability">
                                    {(probability * 100).toFixed(1)}%
                                </span>
                            </div>

                            <div>
                                <span className="recovery-candidate__stat-label">
                                    Candidate action
                                </span>

                                <span className="recovery-candidate__stat-value">
                                    {obligation.prediction?.candidate_action ||
                                        "PAYMENT_LINK"}
                                </span>
                            </div>

                            <div>
                                <span className="recovery-candidate__stat-label">
                                    Model version
                                </span>

                                <span className="recovery-candidate__stat-value recovery-candidate__stat-value--mono">
                                    {obligation.prediction?.model_version || "—"}
                                </span>
                            </div>
                        </div>

                        <div className="recovery-candidate__probability-bar">
                            <div
                                style={{
                                    width: `${Math.min(100, probability * 100)}%`,
                                }}
                            />
                        </div>

                        {state?.error && (
                            <div className="error-banner recovery-candidate__error">
                                {state.error}
                            </div>
                        )}

                        {state?.firewall && (
                            <div
                                className={`recovery-result ${state.firewall.result === "ALLOW"
                                        ? "recovery-result--allow"
                                        : "recovery-result--block"
                                    }`}
                            >
                                <div className="recovery-result__main">
                                    <div>
                                        <span className="recovery-result__label">
                                            Recovery Firewall
                                        </span>

                                        <strong>
                                            {state.firewall.result}
                                        </strong>
                                    </div>

                                    <span className="recovery-result__reason">
                                        {state.firewall.reason}
                                    </span>
                                </div>

                                <div className="recovery-checks">
                                    {Object.entries(state.firewall.checks).map(
                                        ([check, passed]) => (
                                            <div
                                                className="recovery-check"
                                                key={check}
                                            >
                                                <span
                                                    className={
                                                        passed
                                                            ? "recovery-check__icon recovery-check__icon--pass"
                                                            : "recovery-check__icon recovery-check__icon--fail"
                                                    }
                                                >
                                                    {passed ? "✓" : "×"}
                                                </span>

                                                <span>
                                                    {check.replaceAll("_", " ")}
                                                </span>
                                            </div>
                                        )
                                    )}
                                </div>
                            </div>
                        )}

                        <div className="recovery-candidate__footer">
                            <span className="recovery-candidate__action-info">
                                Autonomous action: PAYMENT_LINK
                            </span>

                            <button
                                type="button"
                                className="primary-button"
                                disabled={state?.loading}
                                onClick={() => evaluate(obligation.id)}
                            >
                                {state?.loading
                                    ? "Evaluating..."
                                    : state?.firewall
                                        ? "Evaluate Again"
                                        : "Evaluate Recovery"}
                            </button>
                        </div>
                    </div>
                );
            })}
        </div>
    );
}