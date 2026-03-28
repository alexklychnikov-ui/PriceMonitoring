import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useProducts } from "../hooks/useProducts";
import { formatScraperLabel } from "../utils/siteLabel";
const STORAGE_KEY = "products-filters-v3";
const SHOW_UNAVAILABLE_KEY = "products-show-unavailable";
const PAGE_SIZE = 20;
const EMPTY_FILTERS = {
    name: "",
    brand: "",
    model: "",
    season: "all",
    tireSize: "",
    radius: "",
    spike: "all",
    minPrice: "",
    maxPrice: "",
};
const DEFAULT_SORT = {
    sortBy: "price",
    sortOrder: "asc",
};
function loadSavedFilters() {
    if (typeof window === "undefined") {
        return EMPTY_FILTERS;
    }
    try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        if (!raw) {
            return EMPTY_FILTERS;
        }
        const parsed = JSON.parse(raw);
        return {
            name: parsed.name ?? "",
            brand: parsed.brand ?? "",
            model: parsed.model ?? "",
            season: parsed.season === "winter" || parsed.season === "summer" ? parsed.season : "all",
            tireSize: parsed.tireSize ?? "",
            radius: parsed.radius ?? "",
            spike: parsed.spike === "yes" || parsed.spike === "no" ? parsed.spike : "all",
            minPrice: parsed.minPrice ?? "",
            maxPrice: parsed.maxPrice ?? "",
        };
    }
    catch {
        return EMPTY_FILTERS;
    }
}
function loadSavedSort() {
    if (typeof window === "undefined") {
        return DEFAULT_SORT;
    }
    try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        if (!raw) {
            return DEFAULT_SORT;
        }
        const parsed = JSON.parse(raw);
        const keys = ["name", "brand", "model", "price", "season", "tire_size", "radius", "site_name"];
        const sortBy = keys.includes(parsed.sortBy) ? parsed.sortBy : DEFAULT_SORT.sortBy;
        const sortOrder = parsed.sortOrder === "desc" ? "desc" : "asc";
        return { sortBy, sortOrder };
    }
    catch {
        return DEFAULT_SORT;
    }
}
function sortValue(p, key) {
    if (key === "price") {
        return p.current_price ?? 0;
    }
    if (key === "site_name") {
        return (p.site_name ?? "").toLowerCase();
    }
    if (key === "name") {
        return (p.name ?? "").toLowerCase();
    }
    if (key === "brand") {
        return (p.brand ?? "").toLowerCase();
    }
    if (key === "model") {
        return (p.model ?? "").toLowerCase();
    }
    if (key === "season") {
        return (p.season ?? "").toLowerCase();
    }
    if (key === "tire_size") {
        return (p.tire_size ?? "").toLowerCase();
    }
    if (key === "radius") {
        return (p.radius ?? "").toLowerCase();
    }
    return "";
}
const SORT_COLUMNS = [
    { key: "name", label: "Название" },
    { key: "brand", label: "Бренд" },
    { key: "model", label: "Модель" },
    { key: "season", label: "Сезон" },
    { key: "tire_size", label: "Размер" },
    { key: "radius", label: "Радиус" },
    { key: "site_name", label: "Парсер" },
    { key: "price", label: "Цена" },
];
function loadShowUnavailable() {
    if (typeof window === "undefined") {
        return false;
    }
    try {
        return window.localStorage.getItem(SHOW_UNAVAILABLE_KEY) === "1";
    }
    catch {
        return false;
    }
}
export function ProductsPage() {
    const [showUnavailable, setShowUnavailable] = useState(loadShowUnavailable);
    const { data, isLoading } = useProducts(showUnavailable);
    const navigate = useNavigate();
    const [filters, setFilters] = useState(loadSavedFilters);
    const [sortBy, setSortBy] = useState(() => loadSavedSort().sortBy);
    const [sortOrder, setSortOrder] = useState(() => loadSavedSort().sortOrder);
    const [page, setPage] = useState(1);
    useEffect(() => {
        try {
            window.localStorage.setItem(SHOW_UNAVAILABLE_KEY, showUnavailable ? "1" : "0");
        }
        catch {
            /* ignore */
        }
    }, [showUnavailable]);
    useEffect(() => {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...filters, sortBy, sortOrder }));
    }, [filters, sortBy, sortOrder]);
    const filteredItems = useMemo(() => {
        const items = data?.items ?? [];
        const nameNeedle = filters.name.trim().toLowerCase();
        const brandNeedle = filters.brand.trim().toLowerCase();
        const modelNeedle = filters.model.trim().toLowerCase();
        const tireSizeNeedle = filters.tireSize.trim().toLowerCase();
        const radiusNeedle = filters.radius.trim().toLowerCase();
        const seasonMatchesFilter = (seasonValue) => {
            if (filters.season === "all") {
                return true;
            }
            const normalized = (seasonValue ?? "").trim().toLowerCase();
            if (filters.season === "winter") {
                return normalized === "зима" || normalized === "winter";
            }
            return normalized === "лето" || normalized === "summer";
        };
        const minPrice = Number(filters.minPrice);
        const maxPrice = Number(filters.maxPrice);
        const hasMinPrice = filters.minPrice.trim() !== "" && !Number.isNaN(minPrice);
        const hasMaxPrice = filters.maxPrice.trim() !== "" && !Number.isNaN(maxPrice);
        return items.filter((item) => {
            const nameMatches = item.name.toLowerCase().includes(nameNeedle);
            const brandMatches = (item.brand ?? "").toLowerCase().includes(brandNeedle);
            const modelMatches = (item.model ?? "").toLowerCase().includes(modelNeedle);
            const tireSizeMatches = (item.tire_size ?? "").toLowerCase().includes(tireSizeNeedle);
            const radiusMatches = (item.radius ?? "").toLowerCase().includes(radiusNeedle);
            const spikeMatches = filters.spike === "all" || (filters.spike === "yes" && item.spike === true) || (filters.spike === "no" && item.spike === false);
            const seasonMatches = seasonMatchesFilter(item.season);
            const price = item.current_price;
            const minPriceMatches = !hasMinPrice || (price != null && price >= minPrice);
            const maxPriceMatches = !hasMaxPrice || (price != null && price <= maxPrice);
            return (nameMatches &&
                brandMatches &&
                modelMatches &&
                seasonMatches &&
                tireSizeMatches &&
                radiusMatches &&
                spikeMatches &&
                minPriceMatches &&
                maxPriceMatches);
        });
    }, [data?.items, filters]);
    const sortedItems = useMemo(() => {
        const list = [...filteredItems];
        const mult = sortOrder === "desc" ? -1 : 1;
        list.sort((a, b) => {
            const va = sortValue(a, sortBy);
            const vb = sortValue(b, sortBy);
            if (typeof va === "number" && typeof vb === "number") {
                return (va - vb) * mult;
            }
            return String(va).localeCompare(String(vb), "ru") * mult;
        });
        return list;
    }, [filteredItems, sortBy, sortOrder]);
    const totalPages = Math.max(1, Math.ceil(sortedItems.length / PAGE_SIZE));
    useEffect(() => {
        setPage((prev) => Math.min(prev, totalPages));
    }, [totalPages]);
    const pageItems = useMemo(() => {
        const start = (page - 1) * PAGE_SIZE;
        return sortedItems.slice(start, start + PAGE_SIZE);
    }, [sortedItems, page]);
    const handleFilterChange = (key) => (event) => {
        setFilters((prev) => ({ ...prev, [key]: event.target.value }));
        setPage(1);
    };
    const goToPage = (nextPage) => {
        if (nextPage < 1 || nextPage > totalPages) {
            return;
        }
        setPage(nextPage);
    };
    const resetAllFilters = () => {
        setFilters({ ...EMPTY_FILTERS });
        setSortBy(DEFAULT_SORT.sortBy);
        setSortOrder(DEFAULT_SORT.sortOrder);
        setPage(1);
    };
    const toggleSort = (key) => {
        if (sortBy === key) {
            setSortOrder((o) => (o === "asc" ? "desc" : "asc"));
        }
        else {
            setSortBy(key);
            setSortOrder(key === "price" ? "asc" : "asc");
        }
        setPage(1);
    };
    const headerArrow = (key) => {
        if (sortBy !== key) {
            return "";
        }
        return sortOrder === "asc" ? " ↑" : " ↓";
    };
    if (isLoading) {
        return _jsx("div", { className: "card", children: "\u0417\u0430\u0433\u0440\u0443\u0437\u043A\u0430..." });
    }
    return (_jsxs("div", { className: "card", children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 8, flexWrap: "wrap" }, children: [_jsx("h3", { style: { margin: 0 }, children: "\u041A\u0430\u0442\u0430\u043B\u043E\u0433 \u0442\u043E\u0432\u0430\u0440\u043E\u0432" }), _jsxs("label", { style: { display: "flex", alignItems: "center", gap: 8, cursor: "pointer", userSelect: "none" }, children: [_jsx("input", { type: "checkbox", checked: showUnavailable, onChange: (e) => {
                                    setShowUnavailable(e.target.checked);
                                    setPage(1);
                                } }), "\u041F\u043E\u043A\u0430\u0437\u0430\u0442\u044C \u0441\u043D\u044F\u0442\u044B\u0435 \u0441 \u0432\u0438\u0442\u0440\u0438\u043D\u044B"] }), _jsx("button", { type: "button", onClick: resetAllFilters, children: "\u0421\u0431\u0440\u043E\u0441 \u0432\u0441\u0435\u0445 \u0444\u0438\u043B\u044C\u0442\u0440\u043E\u0432" })] }), _jsxs("table", { style: { width: "100%", borderCollapse: "collapse" }, children: [_jsxs("thead", { children: [_jsxs("tr", { children: [SORT_COLUMNS.map((col) => (_jsx("th", { align: "left", children: _jsxs("button", { type: "button", onClick: () => toggleSort(col.key), style: {
                                                background: "none",
                                                border: "none",
                                                padding: 0,
                                                cursor: "pointer",
                                                font: "inherit",
                                                fontWeight: 700,
                                                textAlign: "left",
                                                color: "inherit",
                                            }, title: "\u0421\u043E\u0440\u0442\u0438\u0440\u043E\u0432\u0430\u0442\u044C", children: [col.label, headerArrow(col.key)] }) }, col.key))), _jsx("th", { align: "left", children: "\u0428\u0438\u043F\u044B" })] }), _jsxs("tr", { children: [_jsx("th", { children: _jsx("input", { value: filters.name, onChange: handleFilterChange("name"), placeholder: "\u0424\u0438\u043B\u044C\u0442\u0440 \u043D\u0430\u0437\u0432\u0430\u043D\u0438\u044F", style: { width: "100%" } }) }), _jsx("th", { children: _jsx("input", { value: filters.brand, onChange: handleFilterChange("brand"), placeholder: "\u0424\u0438\u043B\u044C\u0442\u0440 \u0431\u0440\u0435\u043D\u0434\u0430", style: { width: "100%" } }) }), _jsx("th", { children: _jsx("input", { value: filters.model, onChange: handleFilterChange("model"), placeholder: "\u041C\u043E\u0434\u0435\u043B\u044C", style: { width: "100%" } }) }), _jsx("th", { children: _jsxs("select", { value: filters.season, onChange: (event) => {
                                                setFilters((prev) => ({ ...prev, season: event.target.value }));
                                                setPage(1);
                                            }, style: { width: "100%" }, children: [_jsx("option", { value: "all", children: "\u0412\u0441\u0435" }), _jsx("option", { value: "winter", children: "\u0417\u0438\u043C\u0430" }), _jsx("option", { value: "summer", children: "\u041B\u0435\u0442\u043E" })] }) }), _jsx("th", { children: _jsx("input", { value: filters.tireSize, onChange: handleFilterChange("tireSize"), placeholder: "\u0424\u0438\u043B\u044C\u0442\u0440 \u0440\u0430\u0437\u043C\u0435\u0440\u0430", style: { width: "100%" } }) }), _jsx("th", { children: _jsx("input", { value: filters.radius, onChange: handleFilterChange("radius"), placeholder: "\u0424\u0438\u043B\u044C\u0442\u0440 \u0440\u0430\u0434\u0438\u0443\u0441\u0430", style: { width: "100%" } }) }), _jsx("th", { children: _jsx("span", { style: { opacity: 0.6, fontSize: "0.85em" }, children: "\u2014" }) }), _jsx("th", { children: _jsxs("div", { style: { display: "grid", gap: 4 }, children: [_jsx("input", { value: filters.minPrice, onChange: handleFilterChange("minPrice"), placeholder: "\u0426\u0435\u043D\u0430 \u043E\u0442", inputMode: "numeric", style: { width: "100%" } }), _jsx("input", { value: filters.maxPrice, onChange: handleFilterChange("maxPrice"), placeholder: "\u0426\u0435\u043D\u0430 \u0434\u043E", inputMode: "numeric", style: { width: "100%" } })] }) }), _jsx("th", { children: _jsxs("select", { value: filters.spike, onChange: (event) => {
                                                setFilters((prev) => ({ ...prev, spike: event.target.value }));
                                                setPage(1);
                                            }, style: { width: "100%" }, children: [_jsx("option", { value: "all", children: "\u0412\u0441\u0435" }), _jsx("option", { value: "yes", children: "\u0414\u0430" }), _jsx("option", { value: "no", children: "\u041D\u0435\u0442" })] }) })] })] }), _jsxs("tbody", { children: [pageItems.map((row) => (_jsxs("tr", { onClick: () => navigate(`/products/${row.id}`), style: { cursor: "pointer" }, children: [_jsx("td", { children: row.name }), _jsx("td", { children: row.brand }), _jsx("td", { children: row.model ?? "—" }), _jsx("td", { children: row.season ?? "-" }), _jsx("td", { children: row.tire_size }), _jsx("td", { children: row.radius }), _jsx("td", { style: { fontFamily: "monospace", fontSize: "0.9em" }, children: formatScraperLabel(row.site_name, row.site_id) }), _jsx("td", { children: row.current_price ?? "-" }), _jsx("td", { children: row.spike == null ? "-" : row.spike ? "Да" : "Нет" })] }, row.id))), pageItems.length === 0 && (_jsx("tr", { children: _jsx("td", { colSpan: 9, style: { paddingTop: 12 }, children: "\u041F\u043E \u0432\u044B\u0431\u0440\u0430\u043D\u043D\u044B\u043C \u0444\u0438\u043B\u044C\u0442\u0440\u0430\u043C \u043D\u0438\u0447\u0435\u0433\u043E \u043D\u0435 \u043D\u0430\u0439\u0434\u0435\u043D\u043E." }) }))] })] }), _jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12, gap: 12 }, children: [_jsxs("div", { children: ["\u041F\u043E\u043A\u0430\u0437\u0430\u043D\u043E ", pageItems.length, " \u0438\u0437 ", sortedItems.length] }), _jsxs("div", { style: { display: "flex", gap: 8, alignItems: "center" }, children: [_jsx("button", { type: "button", onClick: () => goToPage(page - 1), disabled: page <= 1, children: "\u041D\u0430\u0437\u0430\u0434" }), _jsxs("span", { children: ["\u0421\u0442\u0440\u0430\u043D\u0438\u0446\u0430 ", page, " / ", totalPages] }), _jsx("button", { type: "button", onClick: () => goToPage(page + 1), disabled: page >= totalPages, children: "\u0412\u043F\u0435\u0440\u0435\u0434" })] })] })] }));
}
