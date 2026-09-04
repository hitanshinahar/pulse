import Link from "next/link";
import { notFound } from "next/navigation";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { TopBar } from "@/components/shell/TopBar";
import {
    fetchObligation,
    fetchObligationTimeline,
} from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/utils";
import type {
    PaymentAttempt,
    ObligationStateTransition,
} from "@/types/api";

interface ObligationDetailPageProps {
    params: Promise<{
        id: string;
    }>;
}

function getTransitionIcon(
    transition: ObligationStateTransition
): string {
    if (transition.new_state === "SATISFIED") return "✓";
    if (transition.new_state === "RECOVERY_ELIGIBLE") return "→";
    if (transition.new_state === "PARTIALLY_SATISFIED") return "◐";
    if (transition.new_state === "ESCALATED") return "!";
    return "•";
}

function PaymentAttemptCard({
    payment,
}: {
    payment: PaymentAttempt;
}) {
    const status = payment.razorpay_status.toLowerCase();

    const statusClass =
        status === "captured"
            ? "badge--satisfied"
            : status === "failed"
                ? "badge--escalated"
                : status === "refunded"
                    ? "badge--partial"
                    : "badge--unresolved";

    return (
        <div className="detail-card">
            <div className="detail-card__header">
                <div>
                    <p className="detail-card__eyebrow">
                        Payment attempt
                    </p>

                    <p className="detail-card__title">
                        {payment.razorpay_payment_id}
                    </p>
                </div>

                <span className={`status-badge ${statusClass}`}>
                    {payment.razorpay_status}
                </span>
            </div>

            <div className="detail-grid detail-grid--four">
                <div>
                    <span className="detail-field__label">
                        Amount
                    </span>

                    <span className="detail-field__value">
                        {formatCurrency(
                            payment.amount,
                            payment.currency
                        )}
                    </span>
                </div>

                <div>
                    <span className="detail-field__label">
                        Method
                    </span>

                    <span className="detail-field__value">
                        {payment.payment_method || "—"}
                    </span>
                </div>

                <div>
                    <span className="detail-field__label">
                        Status
                    </span>

                    <span className="detail-field__value">
                        {payment.razorpay_status}
                    </span>
                </div>

                <div>
                    <span className="detail-field__label">
                        Recorded
                    </span>

                    <span className="detail-field__value">
                        {formatDate(payment.created_at)}
                    </span>
                </div>
            </div>
        </div>
    );
}

function StateTransitionTimeline({
    transitions,
}: {
    transitions: ObligationStateTransition[];
}) {
    if (transitions.length === 0) {
        return (
            <div className="empty-detail">
                <div className="empty-detail__icon">○</div>
                <p>No state transitions recorded.</p>
            </div>
        );
    }

    return (
        <div className="timeline">
            {transitions.map((transition, index) => (
                <div className="timeline__item" key={transition.id}>
                    <div className="timeline__rail">
                        <div className="timeline__dot">
                            {getTransitionIcon(transition)}
                        </div>

                        {index < transitions.length - 1 && (
                            <div className="timeline__line" />
                        )}
                    </div>

                    <div className="timeline__content">
                        <div className="timeline__top">
                            <div>
                                <span className="timeline__transition">
                                    {transition.previous_state || "CREATED"}
                                    <span className="timeline__arrow">→</span>
                                    {transition.new_state}
                                </span>
                            </div>

                            <time className="timeline__date">
                                {formatDate(transition.created_at)}
                            </time>
                        </div>

                        <div className="timeline__meta">
                            <span>
                                Version {transition.previous_version} →{" "}
                                {transition.new_version}
                            </span>

                            {transition.source && (
                                <span>Source: {transition.source}</span>
                            )}
                        </div>

                        {transition.reason && (
                            <p className="timeline__reason">
                                {transition.reason}
                            </p>
                        )}

                        {transition.triggering_event_id && (
                            <p className="timeline__event">
                                Event {transition.triggering_event_id}
                            </p>
                        )}
                    </div>
                </div>
            ))}
        </div>
    );
}

export default async function ObligationDetailPage({
    params,
}: ObligationDetailPageProps) {
    const { id } = await params;

    let obligation;
    let timeline;

    try {
        [obligation, timeline] = await Promise.all([
            fetchObligation(id),
            fetchObligationTimeline(id),
        ]);
    } catch {
        notFound();
    }

    const hasPayments = timeline.payment_attempts.length > 0;
    const hasTransitions = timeline.state_transitions.length > 0;

    const recoveryProgress =
        obligation.amount > 0
            ? Math.min(
                100,
                (obligation.satisfied_amount / obligation.amount) * 100
            )
            : 0;

    return (
        <>
            <TopBar page="Obligation Detail" />
            <div className="page-content animate-in">
                <div className="detail-page">
                    {/* Breadcrumb */}
                    <div className="detail-breadcrumb">
                        <Link href="/obligations" className="back-link">
                            ← Obligations
                        </Link>
                    </div>

                    {/* Header */}
                    <div className="detail-header">
                        <div>
                            <div className="detail-header__eyebrow">
                                FINANCIAL OBLIGATION
                            </div>

                            <div className="detail-header__title-row">
                                <h1 className="detail-header__title">
                                    {obligation.razorpay_order_id}
                                </h1>

                                <StatusBadge status={obligation.status} />
                            </div>

                            <p className="detail-header__subtitle">
                                {obligation.merchant_reference ||
                                    "No merchant reference"}
                            </p>
                        </div>

                        <div className="detail-header__amount">
                            <span className="detail-header__amount-label">
                                Outstanding
                            </span>

                            <span className="detail-header__amount-value">
                                {formatCurrency(
                                    obligation.outstanding_amount,
                                    obligation.currency
                                )}
                            </span>
                        </div>
                    </div>

                    {/* Financial summary */}
                    <section className="detail-section">
                        <div className="section__header">
                            <span className="section__title">
                                Financial State
                            </span>
                        </div>

                        <div className="detail-card">
                            <div className="detail-grid detail-grid--four">
                                <div>
                                    <span className="detail-field__label">
                                        Amount due
                                    </span>
                                    <span className="detail-field__value detail-field__value--large">
                                        {formatCurrency(
                                            obligation.amount,
                                            obligation.currency
                                        )}
                                    </span>
                                </div>

                                <div>
                                    <span className="detail-field__label">
                                        Satisfied
                                    </span>
                                    <span className="detail-field__value detail-field__value--success">
                                        {formatCurrency(
                                            obligation.satisfied_amount,
                                            obligation.currency
                                        )}
                                    </span>
                                </div>

                                <div>
                                    <span className="detail-field__label">
                                        Outstanding
                                    </span>
                                    <span
                                        className={`detail-field__value ${obligation.outstanding_amount > 0
                                            ? "detail-field__value--warning"
                                            : "detail-field__value--success"
                                            }`}
                                    >
                                        {formatCurrency(
                                            obligation.outstanding_amount,
                                            obligation.currency
                                        )}
                                    </span>
                                </div>

                                <div>
                                    <span className="detail-field__label">
                                        State version
                                    </span>
                                    <span className="detail-field__value">
                                        {obligation.state_version}
                                    </span>
                                </div>
                            </div>

                            <div className="recovery-progress">
                                <div className="recovery-progress__header">
                                    <span>Recovery progress</span>
                                    <span>{recoveryProgress.toFixed(0)}%</span>
                                </div>

                                <div className="recovery-progress__track">
                                    <div
                                        className="recovery-progress__bar"
                                        style={{ width: `${recoveryProgress}%` }}
                                    />
                                </div>
                            </div>
                        </div>
                    </section>

                    {/* Recovery lifecycle */}
                    <section className="detail-section">
                        <div className="section__header">
                            <span className="section__title">
                                Recovery Lifecycle
                            </span>
                        </div>

                        <div className="lifecycle">
                            <div className="lifecycle__step lifecycle__step--active">
                                <div className="lifecycle__number">01</div>
                                <div>
                                    <span className="lifecycle__label">
                                        Obligation
                                    </span>
                                    <span className="lifecycle__state">
                                        Created
                                    </span>
                                </div>
                            </div>

                            <div className="lifecycle__connector" />

                            <div
                                className={`lifecycle__step ${obligation.status !== "UNRESOLVED"
                                    ? "lifecycle__step--active"
                                    : ""
                                    }`}
                            >
                                <div className="lifecycle__number">02</div>
                                <div>
                                    <span className="lifecycle__label">
                                        Recovery
                                    </span>
                                    <span className="lifecycle__state">
                                        {obligation.status === "UNRESOLVED"
                                            ? "Pending"
                                            : "Evaluated"}
                                    </span>
                                </div>
                            </div>

                            <div className="lifecycle__connector" />

                            <div
                                className={`lifecycle__step ${hasPayments
                                    ? "lifecycle__step--active"
                                    : ""
                                    }`}
                            >
                                <div className="lifecycle__number">03</div>
                                <div>
                                    <span className="lifecycle__label">
                                        Payment
                                    </span>
                                    <span className="lifecycle__state">
                                        {hasPayments ? "Received" : "Pending"}
                                    </span>
                                </div>
                            </div>

                            <div className="lifecycle__connector" />

                            <div
                                className={`lifecycle__step ${obligation.status === "SATISFIED"
                                    ? "lifecycle__step--success"
                                    : ""
                                    }`}
                            >
                                <div className="lifecycle__number">04</div>
                                <div>
                                    <span className="lifecycle__label">
                                        Recovery
                                    </span>
                                    <span className="lifecycle__state">
                                        {obligation.status === "SATISFIED"
                                            ? "Recovered"
                                            : "Incomplete"}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </section>

                    {/* Payment attempts */}
                    <section className="detail-section">
                        <div className="section__header">
                            <span className="section__title">
                                Payment Attempts
                            </span>

                            <span className="section__count">
                                {timeline.payment_attempts.length}
                            </span>
                        </div>

                        {hasPayments ? (
                            <div className="detail-stack">
                                {timeline.payment_attempts.map((payment) => (
                                    <PaymentAttemptCard
                                        key={payment.id}
                                        payment={payment}
                                    />
                                ))}
                            </div>
                        ) : (
                            <div className="empty-detail">
                                <div className="empty-detail__icon">○</div>
                                <p>No payment attempts recorded.</p>
                                <span>
                                    Payments will appear here when Razorpay events
                                    are processed.
                                </span>
                            </div>
                        )}
                    </section>

                    {/* State timeline */}
                    <section className="detail-section">
                        <div className="section__header">
                            <span className="section__title">
                                State Transitions
                            </span>

                            <span className="section__count">
                                {timeline.state_transitions.length}
                            </span>
                        </div>

                        <div className="detail-card">
                            <StateTransitionTimeline
                                transitions={timeline.state_transitions}
                            />
                        </div>
                    </section>

                    {/* Metadata */}
                    <section className="detail-section">
                        <div className="section__header">
                            <span className="section__title">
                                Obligation Metadata
                            </span>
                        </div>

                        <div className="detail-card">
                            <div className="metadata-grid">
                                <div>
                                    <span className="detail-field__label">
                                        Obligation ID
                                    </span>
                                    <code className="metadata-value">
                                        {obligation.id}
                                    </code>
                                </div>

                                <div>
                                    <span className="detail-field__label">
                                        Razorpay Order
                                    </span>
                                    <code className="metadata-value">
                                        {obligation.razorpay_order_id}
                                    </code>
                                </div>

                                <div>
                                    <span className="detail-field__label">
                                        Created
                                    </span>
                                    <span className="metadata-value">
                                        {formatDate(obligation.created_at)}
                                    </span>
                                </div>

                                <div>
                                    <span className="detail-field__label">
                                        Last updated
                                    </span>
                                    <span className="metadata-value">
                                        {formatDate(obligation.updated_at)}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </section>
                </div>
            </div>
        </>
    );
}