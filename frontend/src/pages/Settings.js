import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useSitesSettings } from "../hooks/useSettings";
export function SettingsPage() {
    const { data, isLoading } = useSitesSettings();
    if (isLoading) {
        return _jsx("div", { className: "card", children: "\u0417\u0430\u0433\u0440\u0443\u0437\u043A\u0430..." });
    }
    return (_jsxs("div", { className: "card", children: [_jsx("h3", { children: "\u041D\u0430\u0441\u0442\u0440\u043E\u0439\u043A\u0438 \u0441\u0430\u0439\u0442\u043E\u0432" }), _jsxs("table", { style: { width: "100%" }, children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { align: "left", children: "\u0421\u0430\u0439\u0442" }), _jsx("th", { align: "left", children: "\u0410\u043A\u0442\u0438\u0432\u0435\u043D" })] }) }), _jsx("tbody", { children: data?.map((site) => (_jsxs("tr", { children: [_jsx("td", { children: site.name }), _jsx("td", { children: site.is_active ? "Да" : "Нет" })] }, site.id))) })] })] }));
}
