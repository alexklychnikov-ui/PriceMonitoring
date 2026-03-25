import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
export function ProductsTable({ items }) {
    return (_jsxs("table", { style: { width: "100%" }, children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { align: "left", children: "\u041D\u0430\u0437\u0432\u0430\u043D\u0438\u0435" }), _jsx("th", { align: "left", children: "\u0426\u0435\u043D\u0430" })] }) }), _jsx("tbody", { children: items.map((item) => (_jsxs("tr", { children: [_jsx("td", { children: item.name }), _jsx("td", { children: item.current_price ?? "-" })] }, item.id))) })] }));
}
