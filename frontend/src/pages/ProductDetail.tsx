import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import { useParams } from "react-router-dom";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fetchProductSubscription, subscribeToProduct, unsubscribeFromProduct } from "../api/client";
import { useProduct, useProductHistory } from "../hooks/useProducts";
import { formatScraperLabel } from "../utils/siteLabel";

const formatRub = new Intl.NumberFormat("ru-RU", { style: "currency", currency: "RUB", maximumFractionDigits: 0 });

export function ProductDetailPage() {
  const { id } = useParams();
  const productId = Number(id);
  const productQuery = useProduct(productId);
  const historyQuery = useProductHistory(productId);
  const queryClient = useQueryClient();

  const chartData = useMemo(
    () =>
      (historyQuery.data || []).map((row) => ({
        date: row.scraped_at.slice(0, 10),
        price: row.price,
      })),
    [historyQuery.data],
  );

  const subQuery = useQuery({
    queryKey: ["product-sub", productId],
    queryFn: () => fetchProductSubscription(productId),
    enabled: Number.isFinite(productId),
  });

  const subscribeMut = useMutation({
    mutationFn: () => subscribeToProduct(productId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["product-sub", productId] });
    },
  });

  const unsubscribeMut = useMutation({
    mutationFn: () => unsubscribeFromProduct(productId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["product-sub", productId] });
    },
  });

  const subscribed = subQuery.data?.subscribed === true;
  const subLoading = subQuery.isFetching || subscribeMut.isPending || unsubscribeMut.isPending;
  const subErr = subQuery.error || subscribeMut.error || unsubscribeMut.error;

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div className="card">
        <h2 style={{ marginTop: 0 }}>{productQuery.data?.name ?? "Товар"}</h2>
        <p style={{ margin: "8px 0", fontFamily: "monospace", fontSize: "0.95em" }}>
          {productQuery.data ? formatScraperLabel(productQuery.data.site_name, productQuery.data.site_id) : "—"}
        </p>
        {productQuery.data?.url ? (
          <p style={{ margin: "0 0 12px" }}>
            <a href={productQuery.data.url} target="_blank" rel="noopener noreferrer">
              Открыть страницу товара в магазине
            </a>
          </p>
        ) : null}
        <div style={{ marginBottom: 12 }}>
          {productQuery.data?.brand} • {productQuery.data?.season} • {productQuery.data?.tire_size} {productQuery.data?.radius}
        </div>

        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
          {!subscribed ? (
            <button type="button" disabled={subLoading} onClick={() => subscribeMut.mutate()}>
              Подписаться на цену
            </button>
          ) : (
            <button type="button" disabled={subLoading} onClick={() => unsubscribeMut.mutate()}>
              Отключить подписку
            </button>
          )}
          {subLoading ? <span style={{ opacity: 0.8 }}>…</span> : null}
        </div>
        {subErr ? (
          <p style={{ color: "#f87171", marginTop: 8, fontSize: "0.9em" }}>
            {(subErr as Error).message || "Ошибка запроса"}
          </p>
        ) : null}
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
