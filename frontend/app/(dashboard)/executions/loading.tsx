export default function ExecutionsLoading() {
    return <DashboardLoading title="Executions" />;
}

function DashboardLoading({ title }: { title: string }) {
    return (
        <div className="page-content" aria-busy="true" aria-label={`Loading ${title}`}>
            <div className="page-header">
                <div className="skeleton" style={{ width: "9rem", height: "1.5rem" }} />
                <div className="skeleton" style={{ width: "20rem", height: "0.9rem", marginTop: "0.75rem" }} />
            </div>
            <section className="section">
                <div className="skeleton" style={{ width: "100%", height: "18rem" }} />
            </section>
        </div>
    );
}
