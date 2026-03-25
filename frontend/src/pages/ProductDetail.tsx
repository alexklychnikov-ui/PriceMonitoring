import { useMemo } from "react";
import { useParams } from "react-router-dom";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useProduct, useProductHistory } from "../hooks/useProducts";

const formatRub = new Intl.NumberFormat("ru-RU", { style: "currency", currency: "RUB", maximumFractionDigits: 0 });

export function ProductDetailPage() {
  const { id } = useParams();
  const productId = Number(id);
  const productQuery = useProduct(productId);
  const historyQuery = useProductHistory(productId);
  const chartData = useMemo(
    () =>
      (historyQuery.data || []).map((row) => ({
        date: row.scraped_at.slice(0, 10),
        price: row.price,
      })),
    [historyQuery.data],
  );

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div className="card">
        <h2>{productQuery.data?.name ?? "Товар"}</h2>
        <div>
          {productQuery.data?.brand} • {productQuery.data?.season} • {productQuery.data?.tire_size} {productQuery.data?.radius}
        </div>
      </div>
      <div className="card" style={{ height: 320 }}>
        <h3>История цен</h3>
        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={chartData}>
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip formatter={(value) => formatRub.format(Number(value))} />
            <Area dataKey="price" stroke="#22c55e" fill="#22c55e33" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
