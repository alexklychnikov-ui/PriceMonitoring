import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useBestDeals, usePriceChanges } from "../hooks/useAnalytics";
export function AnalyticsPage() {
    const changes = usePriceChanges();
    const deals = useBestDeals();
    return (_jsxs("div", { style: { display: "grid", gap: 16 }, children: [_jsxs("div", { className: "card", children: [_jsx("h3", { children: "\u0418\u0437\u043C\u0435\u043D\u0435\u043D\u0438\u044F \u0446\u0435\u043D" }), _jsx("pre", { style: { whiteSpace: "pre-wrap" }, children: JSON.stringify(changes.data?.slice(0, 20) ?? [], null, 2) })] }), _jsxs("div", { className: "card", children: [_jsx("h3", { children: "Best deals" }), _jsx("pre", { style: { whiteSpace: "pre-wrap" }, children: JSON.stringify(deals.data ?? [], null, 2) })] })] }));
}
