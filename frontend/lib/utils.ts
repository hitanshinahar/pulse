import type { ObligationStatus } from "@/types/api";

/**
 * Merge class names — lightweight utility, no external dependency.
 */
export function cn(...classes: (string | undefined | false | null)[]): string {
  return classes.filter(Boolean).join(" ");
}

/**
 * Format a number as currency. Backend amounts are plain numbers (INR by default).
 */
export function formatCurrency(amount: number, currency = "INR"): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

/**
 * Format an ISO 8601 timestamp into a human-readable date+time string.
 */
export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(iso));
}

/**
 * Format seconds into a human-readable duration string.
 */
export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

/**
 * Map obligation status to a display label.
 */
export function statusLabel(status: ObligationStatus): string {
  const map: Record<ObligationStatus, string> = {
    UNRESOLVED: "Unresolved",
    RECOVERY_ELIGIBLE: "Recovery Eligible",
    AMBIGUOUS: "Ambiguous",
    PARTIALLY_SATISFIED: "Partially Satisfied",
    SATISFIED: "Satisfied",
    OVER_COLLECTED: "Over Collected",
    ESCALATED: "Escalated",
    CLOSED: "Closed",
  };
  return map[status] ?? status;
}
