import { useBestDeals, useOverview, usePriceChanges } from "../hooks/useAnalytics";

const formatRub = new Intl.NumberFormat("ru-RU", { style: "currency", currency: "RUB", maximumFractionDigits: 0 });

export function DashboardPage() {
  const overview = useOverview();
  const changes = usePriceChanges();
  const deals = useBestDeals();
  const recentChanges = changes.data?.slice(0, 10) ?? [];
  const bestDeals = deals.data ?? [];

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div className="grid">
        <div className="card">Товаров: {overview.data?.products_count ?? 0}</div>
        <div className="card">Активных сайтов: {overview.data?.active_sites ?? 0}</div>
        <div className="card">Изменений за 24ч: {overview.data?.changes_24h ?? 0}</div>
        <div className="card">Непрочитанных алертов: {overview.data?.unread_alerts ?? 0}</div>
      </div>

      <div className="card">
        <h3>Последние изменения цен</h3>
        <ul>
          {recentChanges.length === 0 ? (
            <li>Нет данных</li>
          ) : (
            recentChanges.map((row, idx) => (
              <li key={String(row.alert_id ?? row.product_id ?? idx)}>
                {String(row.product_name)} ({String(row.site_name)}): {String(row.old_price ?? "-")} →{" "}
                {String(row.new_price ?? "-")}
              </li>
            ))
          )}
        </ul>
      </div>

      <div className="card">
        <h3>Лучшие предложения</h3>
        <ul>
          {bestDeals.length === 0 ? (
            <li>Нет данных</li>
          ) : (
            bestDeals.map((deal, idx) => (
              <li key={String(deal.product_id ?? deal.name ?? idx)}>
                {String(deal.name)} ({String(deal.site_name)}) — {formatRub.format(Number(deal.price ?? 0))}
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
}
