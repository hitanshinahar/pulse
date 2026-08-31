/**
 * RecoveryFunnel — pure visual, no API call needed.
 * Represents the Pulse product lifecycle architecture.
 */

const steps = [
  { label: "Obligation", num: "1", color: "muted" as const },
  { label: "Decision", num: "2", color: "active" as const },
  { label: "Firewall", num: "3", color: "active" as const },
  { label: "Execution", num: "4", color: "active" as const },
  { label: "Payment", num: "5", color: "active" as const },
  { label: "Recovered", num: "✓", color: "success" as const },
];

export function RecoveryFunnel() {
  return (
    <div className="funnel" role="img" aria-label="Recovery lifecycle funnel">
      {steps.map((step, i) => (
        <div key={step.label} className="funnel__step">
          <div className="funnel__node">
            <div className={`funnel__dot funnel__dot--${step.color}`}>
              {step.num}
            </div>
            <span className="funnel__label">{step.label}</span>
          </div>
          {i < steps.length - 1 && (
            <span className="funnel__arrow" aria-hidden="true">→</span>
          )}
        </div>
      ))}
    </div>
  );
}
