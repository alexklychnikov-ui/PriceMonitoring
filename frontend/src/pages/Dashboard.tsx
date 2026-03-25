import { useBestDeals, useOverview, usePriceChanges } from "../hooks/useAnalytics";

const formatRub = new Intl.NumberFormat("ru-RU", { style: "currency", currency: "RUB", maximumFractionDigits: 0 });

export function DashboardPage() {
  const overview = useOverview();
  const changes = usePriceChanges();
  const deals = useBestDeals();

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
          {changes.data?.slice(0, 10).map((row, idx) => (
            <li key={idx}>
              {String(row.product_name)}: {String(row.old_price)} → {String(row.new_price)}
            </li>
          )) || <li>Нет данных</li>}
        </ul>
      </div>

      <div className="card">
        <h3>Лучшие предложения</h3>
        <ul>
          {deals.data?.map((deal, idx) => (
            <li key={idx}>
              {String(deal.name)} — {formatRub.format(Number(deal.price ?? 0))}
            </li>
          )) || <li>Нет данных</li>}
        </ul>
      </div>
    </div>
  );
}
