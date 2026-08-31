export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} aria-hidden="true" />;
}

export function SkeletonRow({ cols = 4 }: { cols?: number }) {
  return (
    <tr className="skeleton-row" aria-hidden="true">
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="table-cell">
          <Skeleton className="h-4 w-full" />
        </td>
      ))}
    </tr>
  );
}
