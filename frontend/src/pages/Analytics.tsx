import { useBestDeals, usePriceChanges } from "../hooks/useAnalytics";

export function AnalyticsPage() {
  const changes = usePriceChanges();
  const deals = useBestDeals();

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div className="card">
        <h3>Изменения цен</h3>
        <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(changes.data?.slice(0, 20) ?? [], null, 2)}</pre>
      </div>
      <div className="card">
        <h3>Best deals</h3>
        <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(deals.data ?? [], null, 2)}</pre>
      </div>
    </div>
  );
}
