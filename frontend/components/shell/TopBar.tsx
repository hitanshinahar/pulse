interface TopBarProps {
  page: string;
}

export function TopBar({ page }: TopBarProps) {
  return (
    <header className="topbar">
      <div className="topbar__left">
        <span className="topbar__breadcrumb">Pulse</span>
        <span className="topbar__breadcrumb-sep" aria-hidden="true">/</span>
        <span className="topbar__page">{page}</span>
      </div>

      <div className="topbar__right">
        <span
          style={{
            fontSize: "11px",
            color: "var(--text-tertiary)",
            fontFamily: "var(--font-mono)",
          }}
        >
          {(() => {
            try {
              return process.env.NEXT_PUBLIC_API_URL
                ? new URL(process.env.NEXT_PUBLIC_API_URL).hostname
                : "—";
            } catch {
              return process.env.NEXT_PUBLIC_API_URL ?? "—";
            }
          })()}
        </span>
      </div>
    </header>
  );
}
