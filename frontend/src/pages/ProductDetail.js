import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
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
    const chartData = useMemo(() => (historyQuery.data || []).map((row) => ({
        date: row.scraped_at.slice(0, 10),
        price: row.price,
    })), [historyQuery.data]);
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
    return (_jsxs("div", { style: { display: "grid", gap: 16 }, children: [_jsxs("div", { className: "card", children: [_jsx("h2", { style: { marginTop: 0 }, children: productQuery.data?.name ?? "Товар" }), _jsx("p", { style: { margin: "8px 0", fontFamily: "monospace", fontSize: "0.95em" }, children: productQuery.data ? formatScraperLabel(productQuery.data.site_name, productQuery.data.site_id) : "—" }), productQuery.data?.url ? (_jsx("p", { style: { margin: "0 0 12px" }, children: _jsx("a", { href: productQuery.data.url, target: "_blank", rel: "noopener noreferrer", children: "\u041E\u0442\u043A\u0440\u044B\u0442\u044C \u0441\u0442\u0440\u0430\u043D\u0438\u0446\u0443 \u0442\u043E\u0432\u0430\u0440\u0430 \u0432 \u043C\u0430\u0433\u0430\u0437\u0438\u043D\u0435" }) })) : null, _jsxs("div", { style: { marginBottom: 12 }, children: [productQuery.data?.brand, " \u2022 ", productQuery.data?.season, " \u2022 ", productQuery.data?.tire_size, " ", productQuery.data?.radius] }), _jsxs("div", { style: { display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }, children: [!subscribed ? (_jsx("button", { type: "button", disabled: subLoading, onClick: () => subscribeMut.mutate(), children: "\u041F\u043E\u0434\u043F\u0438\u0441\u0430\u0442\u044C\u0441\u044F \u043D\u0430 \u0446\u0435\u043D\u0443" })) : (_jsx("button", { type: "button", disabled: subLoading, onClick: () => unsubscribeMut.mutate(), children: "\u041E\u0442\u043A\u043B\u044E\u0447\u0438\u0442\u044C \u043F\u043E\u0434\u043F\u0438\u0441\u043A\u0443" })), subLoading ? _jsx("span", { style: { opacity: 0.8 }, children: "\u2026" }) : null] }), subErr ? (_jsx("p", { style: { color: "#f87171", marginTop: 8, fontSize: "0.9em" }, children: subErr.message || "Ошибка запроса" })) : null] }), _jsxs("div", { className: "card", style: { height: 320 }, children: [_jsx("h3", { children: "\u0418\u0441\u0442\u043E\u0440\u0438\u044F \u0446\u0435\u043D" }), _jsx(ResponsiveContainer, { width: "100%", height: 240, children: _jsxs(AreaChart, { data: chartData, children: [_jsx(XAxis, { dataKey: "date" }), _jsx(YAxis, {}), _jsx(Tooltip, { formatter: (value) => formatRub.format(Number(value)) }), _jsx(Area, { dataKey: "price", stroke: "#22c55e", fill: "#22c55e33" })] }) })] })] }));
}
