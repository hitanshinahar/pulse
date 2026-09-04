"use client";

import { useState } from "react";

import type { Obligation, RecoveryDecisionListItem } from "@/types/api";
import {
    createRecoveryDecision,
    evaluateRecoveryDecision,
    fetchRecoveryDecisions,
} from "@/lib/api";

interface RecoveryCandidateProps {
    obligation: Obligation;
    initialDecisions: RecoveryDecisionListItem[];
}

interface DecisionResponse {
    id: string;
    obligation_id: string;
    action: string;
    baseline_probability: number | null;
    action_probability: number | null;
    incremental_probability: number | null;
    expected_incremental_amount: number | null;
    state_version: number;
    model_version: string | null;
    status: string;
    llm_diagnosis: string | null;
}

interface EvaluationResponse {
    decision_id: string;
    result: string;
    reason_code: string;
    reason: string;
    checks: Record<string, unknown>;
    state_version_expected: number;
    state_version_actual: number;
}

interface AuditExecution {
    id: string;
    status: string;
    idempotency_key: string | null;
    executed_at: string | null;
}

interface AuditResponse {
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
        checks: Record<string, unknown>;
        created_at: string;
    }>;
    executions: AuditExecution[];
}

interface ExecutionResponse {
    id: string;
    status: string;
    razorpay_reference_id: string | null;
    razorpay_payment_link_id: string | null;
    short_url: string | null;
    executed_at: string | null;
}

function formatCurrency(amount: number, currency = "INR") {
    return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency,
        maximumFractionDigits: 0,
    }).format(amount);
}

function formatDate(value: string | null) {
    if (!value) return "—";

    return new Intl.DateTimeFormat("en-IN", {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(new Date(value));
}

function StatusBadge({ status }: { status: string }) {
    const normalized = status.toUpperCase();

    const className =
        normalized === "ALLOW" ||
            normalized === "EXECUTED" ||
            normalized === "AUTHORIZED_PENDING_EXECUTION" ||
            normalized === "AUTHORIZED"
            ? "status-badge status-badge--success"
            : normalized === "BLOCK" ||
                normalized === "EXECUTION_FAILED"
                ? "status-badge status-badge--danger"
                : "status-badge status-badge--warning";

    return <span className={className}>{status}</span>;
}

export default function RecoveryCandidate({
    obligation,
    initialDecisions,
}: RecoveryCandidateProps) {
    const [decisions, setDecisions] =
        useState<RecoveryDecisionListItem[]>(initialDecisions);

    const [decision, setDecision] =
        useState<DecisionResponse | null>(null);

    const [evaluation, setEvaluation] =
        useState<EvaluationResponse | null>(null);

    const [execution, setExecution] =
        useState<ExecutionResponse | null>(null);

    const [loading, setLoading] = useState(false);
    const [evaluating, setEvaluating] = useState(false);
    const [executing, setExecuting] = useState(false);
    const [reconciling, setReconciling] = useState(false);
    const [error, setError] = useState<string | null>(null);

    async function generateDecision() {
        setLoading(true);
        setError(null);
        setEvaluation(null);
        setExecution(null);

        try {
            const response = (await createRecoveryDecision(
                obligation.id
            )) as DecisionResponse;

            setDecision(response);

            const refreshed =
                await fetchRecoveryDecisions(obligation.id);

            setDecisions(refreshed);
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Unable to generate recovery decision."
            );
        } finally {
            setLoading(false);
        }
    }

    async function evaluateDecision() {
        if (!decision) return;

        setEvaluating(true);
        setError(null);

        try {
            const result = (await evaluateRecoveryDecision(
                decision.id
            )) as EvaluationResponse;

            setEvaluation(result);

            if (result.result === "ALLOW") {
                const auditResponse = await fetch(
                    `/api/recovery/audit/${decision.id}`,
                    {
                        method: "GET",
                        cache: "no-store",
                    }
                );

                if (!auditResponse.ok) {
                    throw new Error(
                        "Firewall allowed the action, but execution could not be loaded."
                    );
                }

                const audit =
                    (await auditResponse.json()) as AuditResponse;

                const authorizedExecution =
                    audit.executions?.find(
                        (item) =>
                            item.status ===
                            "AUTHORIZED_PENDING_EXECUTION" ||
                            item.status === "AUTHORIZED"
                    );

                if (!authorizedExecution) {
                    throw new Error(
                        "Recovery was authorized, but no executable recovery was found."
                    );
                }

                setExecution({
                    id: authorizedExecution.id,
                    status: authorizedExecution.status,
                    razorpay_reference_id: null,
                    razorpay_payment_link_id: null,
                    short_url: null,
                    executed_at: authorizedExecution.executed_at,
                });
            }
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Unable to evaluate recovery decision."
            );
        } finally {
            setEvaluating(false);
        }
    }

    async function executeRecovery() {
        if (!execution) return;

        setExecuting(true);
        setError(null);

        try {
            const response = await fetch(
                `/api/recovery/execution/${execution.id}`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                }
            );

            const data =
                (await response.json()) as ExecutionResponse & {
                    detail?: string;
                };

            if (!response.ok) {
                throw new Error(
                    data.detail || "Unable to execute recovery."
                );
            }

            setExecution(data);
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Unable to execute recovery."
            );
        } finally {
            setExecuting(false);
        }
    }

    async function reconcileExecution() {
        if (!execution) return;

        setReconciling(true);
        setError(null);

        try {
            const response = await fetch(
                `/api/recovery/execution/${execution.id}/reconcile`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                }
            );

            const data =
                (await response.json()) as ExecutionResponse & {
                    detail?: string;
                };

            if (!response.ok) {
                throw new Error(
                    data.detail || "Unable to reconcile execution."
                );
            }

            setExecution((current) => ({
                ...(current || data),
                ...data,
            }));
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Unable to reconcile execution."
            );
        } finally {
            setReconciling(false);
        }
    }

    return (
        <article className="recovery-candidate">
            <header className="recovery-candidate__header">
                <div>
                    <div className="recovery-candidate__order">
                        {obligation.merchant_reference ||
                            obligation.razorpay_order_id}
                    </div>

                    <div className="recovery-candidate__updated">
                        Updated {formatDate(obligation.updated_at)}
                    </div>
                </div>

                <div className="recovery-candidate__status">
                    <StatusBadge status={obligation.status} />
                </div>
            </header>

            <section className="recovery-candidate__financial">
                <div className="recovery-field">
                    <span>Original amount</span>
                    <strong>
                        {formatCurrency(
                            obligation.amount,
                            obligation.currency
                        )}
                    </strong>
                </div>

                <div className="recovery-field">
                    <span>Satisfied</span>
                    <strong>
                        {formatCurrency(
                            obligation.satisfied_amount,
                            obligation.currency
                        )}
                    </strong>
                </div>

                <div className="recovery-field">
                    <span>Outstanding</span>
                    <strong>
                        {formatCurrency(
                            obligation.outstanding_amount,
                            obligation.currency
                        )}
                    </strong>
                </div>
            </section>

            <section className="recovery-engine">
                <div className="recovery-engine__header">
                    <div>
                        <div className="recovery-engine__title">
                            Recovery Engine
                        </div>

                        <div className="recovery-engine__subtitle">
                            AI diagnosis → deterministic policy →
                            bounded execution
                        </div>
                    </div>

                    <div className="recovery-engine__status">
                        <span className="status-dot" />
                        ACTIVE
                    </div>
                </div>

                {!decision && (
                    <div className="recovery-engine__empty">
                        <p>
                            No recovery decision has been generated
                            for this obligation.
                        </p>

                        <button
                            className="button button--primary"
                            onClick={generateDecision}
                            disabled={loading}
                        >
                            {loading
                                ? "Generating…"
                                : "Generate Recovery Decision"}
                        </button>
                    </div>
                )}

                {decision && (
                    <>
                        <div className="recovery-decision">
                            <div className="recovery-decision__header">
                                <div>
                                    <span className="recovery-decision__eyebrow">
                                        PROPOSED ACTION
                                    </span>

                                    <h3>
                                        {decision.action}
                                    </h3>
                                </div>

                                <StatusBadge
                                    status={decision.status}
                                />
                            </div>

                            <div className="recovery-decision__metrics">
                                <div>
                                    <span>
                                        Baseline probability
                                    </span>
                                    <strong>
                                        {decision.baseline_probability !==
                                            null
                                            ? `${(
                                                decision.baseline_probability *
                                                100
                                            ).toFixed(1)}%`
                                            : "—"}
                                    </strong>
                                </div>

                                <div>
                                    <span>
                                        Action probability
                                    </span>
                                    <strong>
                                        {decision.action_probability !==
                                            null
                                            ? `${(
                                                decision.action_probability *
                                                100
                                            ).toFixed(1)}%`
                                            : "—"}
                                    </strong>
                                </div>

                                <div>
                                    <span>
                                        Incremental probability
                                    </span>
                                    <strong>
                                        {decision.incremental_probability !==
                                            null
                                            ? `${(
                                                decision.incremental_probability *
                                                100
                                            ).toFixed(1)}%`
                                            : "—"}
                                    </strong>
                                </div>

                                <div>
                                    <span>
                                        Expected incremental recovery
                                    </span>
                                    <strong>
                                        {decision.expected_incremental_amount !==
                                            null
                                            ? formatCurrency(
                                                decision.expected_incremental_amount,
                                                obligation.currency
                                            )
                                            : "—"}
                                    </strong>
                                </div>
                            </div>

                            {decision.llm_diagnosis && (
                                <div className="recovery-decision__diagnosis">
                                    <span>AI diagnosis</span>
                                    <p>
                                        {decision.llm_diagnosis}
                                    </p>
                                </div>
                            )}
                        </div>

                        {!evaluation && (
                            <div className="recovery-engine__actions">
                                <button
                                    className="button button--primary"
                                    onClick={evaluateDecision}
                                    disabled={evaluating}
                                >
                                    {evaluating
                                        ? "Running Firewall…"
                                        : "Evaluate with Firewall"}
                                </button>
                            </div>
                        )}

                        {evaluation && (
                            <div className="recovery-firewall">
                                <div className="recovery-firewall__header">
                                    <div>
                                        <span className="recovery-decision__eyebrow">
                                            RUNTIME AUTHORITY
                                        </span>

                                        <h3>
                                            Firewall Result
                                        </h3>
                                    </div>

                                    <StatusBadge
                                        status={evaluation.result}
                                    />
                                </div>

                                <div className="recovery-decision__metrics">
                                    <div>
                                        <span>Reason code</span>
                                        <strong>
                                            {evaluation.reason_code}
                                        </strong>
                                    </div>

                                    <div>
                                        <span>Expected state</span>
                                        <strong>
                                            v
                                            {
                                                evaluation.state_version_expected
                                            }
                                        </strong>
                                    </div>

                                    <div>
                                        <span>Actual state</span>
                                        <strong>
                                            v
                                            {
                                                evaluation.state_version_actual
                                            }
                                        </strong>
                                    </div>
                                </div>

                                <div className="recovery-decision-notice">
                                    {evaluation.reason}
                                </div>

                                {evaluation.result === "ALLOW" &&
                                    execution && (
                                        <div className="recovery-engine__actions">
                                            {execution.status ===
                                                "AUTHORIZED_PENDING_EXECUTION" ||
                                                execution.status ===
                                                "AUTHORIZED" ? (
                                                <button
                                                    className="button button--primary"
                                                    onClick={
                                                        executeRecovery
                                                    }
                                                    disabled={
                                                        executing
                                                    }
                                                >
                                                    {executing
                                                        ? "Executing…"
                                                        : "Execute Recovery"}
                                                </button>
                                            ) : null}

                                            {execution.status ===
                                                "EXECUTED" && (
                                                    <div className="recovery-execution">
                                                        <div className="recovery-decision-notice">
                                                            Recovery executed successfully.
                                                        </div>

                                                        {execution.razorpay_payment_link_id && (
                                                            <div className="recovery-decision__metrics">
                                                                <div>
                                                                    <span>
                                                                        Razorpay Payment Link
                                                                    </span>
                                                                    <strong>
                                                                        {
                                                                            execution.razorpay_payment_link_id
                                                                        }
                                                                    </strong>
                                                                </div>

                                                                <div>
                                                                    <span>
                                                                        Reference
                                                                    </span>
                                                                    <strong>
                                                                        {
                                                                            execution.razorpay_reference_id
                                                                        }
                                                                    </strong>
                                                                </div>

                                                                <div>
                                                                    <span>
                                                                        Executed
                                                                    </span>
                                                                    <strong>
                                                                        {formatDate(
                                                                            execution.executed_at
                                                                        )}
                                                                    </strong>
                                                                </div>
                                                            </div>
                                                        )}

                                                        {execution.short_url && (
                                                            <div className="recovery-engine__actions">
                                                                <a
                                                                    className="button button--primary"
                                                                    href={
                                                                        execution.short_url
                                                                    }
                                                                    target="_blank"
                                                                    rel="noreferrer"
                                                                >
                                                                    Open Razorpay Payment Link
                                                                </a>
                                                            </div>
                                                        )}
                                                    </div>
                                                )}

                                            {execution.status ===
                                                "EXECUTION_UNKNOWN" && (
                                                    <div className="recovery-execution">
                                                        <div className="recovery-decision-notice">
                                                            Execution status is unknown. Reconcile with Razorpay before retrying.
                                                        </div>

                                                        <button
                                                            className="button button--secondary"
                                                            onClick={
                                                                reconcileExecution
                                                            }
                                                            disabled={
                                                                reconciling
                                                            }
                                                        >
                                                            {reconciling
                                                                ? "Reconciling…"
                                                                : "Reconcile Execution"}
                                                        </button>
                                                    </div>
                                                )}

                                            {execution.status ===
                                                "EXECUTION_FAILED" && (
                                                    <div className="recovery-decision-notice">
                                                        Recovery execution failed. No automatic retry was performed.
                                                    </div>
                                                )}
                                        </div>
                                    )}
                            </div>
                        )}
                    </>
                )}

                {error && (
                    <div className="recovery-error">
                        {error}
                    </div>
                )}
            </section>

            {decisions.length > 0 && (
                <section className="recovery-decision-history">
                    <div className="recovery-decision__eyebrow">
                        DECISION HISTORY
                    </div>

                    {decisions.map((item) => (
                        <div
                            className="recovery-decision-history__row"
                            key={item.id}
                        >
                            <span>{item.action}</span>
                            <StatusBadge status={item.status} />
                            <strong>
                                {item.expected_incremental_amount !==
                                    null
                                    ? formatCurrency(
                                        item.expected_incremental_amount,
                                        obligation.currency
                                    )
                                    : "—"}
                            </strong>
                        </div>
                    ))}
                </section>
            )}
        </article>
    );
}