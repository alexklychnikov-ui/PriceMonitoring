import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
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
    const chartData = useMemo(() => (historyQuery.data || []).map((row) => ({
        date: row.scraped_at.slice(0, 10),
        price: row.price,
    })), [historyQuery.data]);
    return (_jsxs("div", { style: { display: "grid", gap: 16 }, children: [_jsxs("div", { className: "card", children: [_jsx("h2", { children: productQuery.data?.name ?? "Товар" }), _jsxs("div", { children: [productQuery.data?.brand, " \u2022 ", productQuery.data?.season, " \u2022 ", productQuery.data?.tire_size, " ", productQuery.data?.radius] })] }), _jsxs("div", { className: "card", style: { height: 320 }, children: [_jsx("h3", { children: "\u0418\u0441\u0442\u043E\u0440\u0438\u044F \u0446\u0435\u043D" }), _jsx(ResponsiveContainer, { width: "100%", height: 240, children: _jsxs(AreaChart, { data: chartData, children: [_jsx(XAxis, { dataKey: "date" }), _jsx(YAxis, {}), _jsx(Tooltip, { formatter: (value) => formatRub.format(Number(value)) }), _jsx(Area, { dataKey: "price", stroke: "#22c55e", fill: "#22c55e33" })] }) })] })] }));
}
