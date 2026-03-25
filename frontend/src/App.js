import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { NavLink, Route, Routes } from "react-router-dom";
import { DashboardPage } from "./pages/Dashboard";
import { ProductsPage } from "./pages/Products";
import { ProductDetailPage } from "./pages/ProductDetail";
import { AnalyticsPage } from "./pages/Analytics";
import { SettingsPage } from "./pages/Settings";
export function App() {
    return (_jsxs("div", { className: "container", children: [_jsxs("nav", { style: { display: "flex", gap: 12, marginBottom: 16 }, children: [_jsx(NavLink, { to: "/", children: "Dashboard" }), _jsx(NavLink, { to: "/products", children: "Products" }), _jsx(NavLink, { to: "/analytics", children: "Analytics" }), _jsx(NavLink, { to: "/settings", children: "Settings" })] }), _jsxs(Routes, { children: [_jsx(Route, { path: "/", element: _jsx(DashboardPage, {}) }), _jsx(Route, { path: "/products", element: _jsx(ProductsPage, {}) }), _jsx(Route, { path: "/products/:id", element: _jsx(ProductDetailPage, {}) }), _jsx(Route, { path: "/analytics", element: _jsx(AnalyticsPage, {}) }), _jsx(Route, { path: "/settings", element: _jsx(SettingsPage, {}) })] })] }));
}
