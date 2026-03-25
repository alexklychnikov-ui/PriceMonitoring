import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useNavigate } from "react-router-dom";
import { useProducts } from "../hooks/useProducts";
export function ProductsPage() {
    const { data, isLoading } = useProducts();
    const navigate = useNavigate();
    if (isLoading) {
        return _jsx("div", { className: "card", children: "\u0417\u0430\u0433\u0440\u0443\u0437\u043A\u0430..." });
    }
    return (_jsxs("div", { className: "card", children: [_jsx("h3", { children: "\u041A\u0430\u0442\u0430\u043B\u043E\u0433 \u0442\u043E\u0432\u0430\u0440\u043E\u0432" }), _jsxs("table", { style: { width: "100%", borderCollapse: "collapse" }, children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { align: "left", children: "\u041D\u0430\u0437\u0432\u0430\u043D\u0438\u0435" }), _jsx("th", { align: "left", children: "\u0411\u0440\u0435\u043D\u0434" }), _jsx("th", { align: "left", children: "\u0420\u0430\u0437\u043C\u0435\u0440" }), _jsx("th", { align: "left", children: "\u0420\u0430\u0434\u0438\u0443\u0441" }), _jsx("th", { align: "left", children: "\u0426\u0435\u043D\u0430" })] }) }), _jsx("tbody", { children: data?.items.map((row) => (_jsxs("tr", { onClick: () => navigate(`/products/${row.id}`), style: { cursor: "pointer" }, children: [_jsx("td", { children: row.name }), _jsx("td", { children: row.brand }), _jsx("td", { children: row.tire_size }), _jsx("td", { children: row.radius }), _jsx("td", { children: row.current_price ?? "-" })] }, row.id))) })] })] }));
}
