import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useProducts } from "../hooks/useProducts";
const STORAGE_KEY = "products-filters-v2";
const PAGE_SIZE = 20;
const EMPTY_FILTERS = {
    name: "",
    brand: "",
    season: "all",
    tireSize: "",
    radius: "",
    spike: "all",
    minPrice: "",
    maxPrice: "",
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
export function ProductsPage() {
    const { data, isLoading } = useProducts();
    const navigate = useNavigate();
    const [filters, setFilters] = useState(loadSavedFilters);
    const [page, setPage] = useState(1);
    useEffect(() => {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(filters));
    }, [filters]);
    const filteredItems = useMemo(() => {
        const items = data?.items ?? [];
        const nameNeedle = filters.name.trim().toLowerCase();
        const brandNeedle = filters.brand.trim().toLowerCase();
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
            const tireSizeMatches = (item.tire_size ?? "").toLowerCase().includes(tireSizeNeedle);
            const radiusMatches = (item.radius ?? "").toLowerCase().includes(radiusNeedle);
            const spikeMatches = filters.spike === "all" || (filters.spike === "yes" && item.spike === true) || (filters.spike === "no" && item.spike === false);
            const seasonMatches = seasonMatchesFilter(item.season);
            const price = item.current_price;
            const minPriceMatches = !hasMinPrice || (price != null && price >= minPrice);
            const maxPriceMatches = !hasMaxPrice || (price != null && price <= maxPrice);
            return nameMatches && brandMatches && seasonMatches && tireSizeMatches && radiusMatches && spikeMatches && minPriceMatches && maxPriceMatches;
        });
    }, [data?.items, filters]);
    const totalPages = Math.max(1, Math.ceil(filteredItems.length / PAGE_SIZE));
    useEffect(() => {
        setPage((prev) => Math.min(prev, totalPages));
    }, [totalPages]);
    const pageItems = useMemo(() => {
        const start = (page - 1) * PAGE_SIZE;
        return filteredItems.slice(start, start + PAGE_SIZE);
    }, [filteredItems, page]);
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
        setPage(1);
    };
    if (isLoading) {
        return _jsx("div", { className: "card", children: "\u0417\u0430\u0433\u0440\u0443\u0437\u043A\u0430..." });
    }
    return (_jsxs("div", { className: "card", children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 8 }, children: [_jsx("h3", { style: { margin: 0 }, children: "\u041A\u0430\u0442\u0430\u043B\u043E\u0433 \u0442\u043E\u0432\u0430\u0440\u043E\u0432" }), _jsx("button", { type: "button", onClick: resetAllFilters, children: "\u0421\u0431\u0440\u043E\u0441 \u0432\u0441\u0435\u0445 \u0444\u0438\u043B\u044C\u0442\u0440\u043E\u0432" })] }), _jsxs("table", { style: { width: "100%", borderCollapse: "collapse" }, children: [_jsxs("thead", { children: [_jsxs("tr", { children: [_jsx("th", { align: "left", children: "\u041D\u0430\u0437\u0432\u0430\u043D\u0438\u0435" }), _jsx("th", { align: "left", children: "\u0411\u0440\u0435\u043D\u0434" }), _jsx("th", { align: "left", children: "\u0421\u0435\u0437\u043E\u043D" }), _jsx("th", { align: "left", children: "\u0420\u0430\u0437\u043C\u0435\u0440" }), _jsx("th", { align: "left", children: "\u0420\u0430\u0434\u0438\u0443\u0441" }), _jsx("th", { align: "left", children: "\u0428\u0438\u043F\u044B" }), _jsx("th", { align: "left", children: "\u0426\u0435\u043D\u0430" })] }), _jsxs("tr", { children: [_jsx("th", { children: _jsx("input", { value: filters.name, onChange: handleFilterChange("name"), placeholder: "\u0424\u0438\u043B\u044C\u0442\u0440 \u043D\u0430\u0437\u0432\u0430\u043D\u0438\u044F", style: { width: "100%" } }) }), _jsx("th", { children: _jsx("input", { value: filters.brand, onChange: handleFilterChange("brand"), placeholder: "\u0424\u0438\u043B\u044C\u0442\u0440 \u0431\u0440\u0435\u043D\u0434\u0430", style: { width: "100%" } }) }), _jsx("th", { children: _jsxs("select", { value: filters.season, onChange: (event) => {
                                                setFilters((prev) => ({ ...prev, season: event.target.value }));
                                                setPage(1);
                                            }, style: { width: "100%" }, children: [_jsx("option", { value: "all", children: "\u0412\u0441\u0435" }), _jsx("option", { value: "winter", children: "\u0417\u0438\u043C\u0430" }), _jsx("option", { value: "summer", children: "\u041B\u0435\u0442\u043E" })] }) }), _jsx("th", { children: _jsx("input", { value: filters.tireSize, onChange: handleFilterChange("tireSize"), placeholder: "\u0424\u0438\u043B\u044C\u0442\u0440 \u0440\u0430\u0437\u043C\u0435\u0440\u0430", style: { width: "100%" } }) }), _jsx("th", { children: _jsx("input", { value: filters.radius, onChange: handleFilterChange("radius"), placeholder: "\u0424\u0438\u043B\u044C\u0442\u0440 \u0440\u0430\u0434\u0438\u0443\u0441\u0430", style: { width: "100%" } }) }), _jsx("th", { children: _jsxs("select", { value: filters.spike, onChange: (event) => {
                                                setFilters((prev) => ({ ...prev, spike: event.target.value }));
                                                setPage(1);
                                            }, style: { width: "100%" }, children: [_jsx("option", { value: "all", children: "\u0412\u0441\u0435" }), _jsx("option", { value: "yes", children: "\u0414\u0430" }), _jsx("option", { value: "no", children: "\u041D\u0435\u0442" })] }) }), _jsx("th", { children: _jsxs("div", { style: { display: "grid", gap: 4 }, children: [_jsx("input", { value: filters.minPrice, onChange: handleFilterChange("minPrice"), placeholder: "\u0426\u0435\u043D\u0430 \u043E\u0442", inputMode: "numeric", style: { width: "100%" } }), _jsx("input", { value: filters.maxPrice, onChange: handleFilterChange("maxPrice"), placeholder: "\u0426\u0435\u043D\u0430 \u0434\u043E", inputMode: "numeric", style: { width: "100%" } })] }) })] })] }), _jsxs("tbody", { children: [pageItems.map((row) => (_jsxs("tr", { onClick: () => navigate(`/products/${row.id}`), style: { cursor: "pointer" }, children: [_jsx("td", { children: row.name }), _jsx("td", { children: row.brand }), _jsx("td", { children: row.season ?? "-" }), _jsx("td", { children: row.tire_size }), _jsx("td", { children: row.radius }), _jsx("td", { children: row.spike == null ? "-" : row.spike ? "Да" : "Нет" }), _jsx("td", { children: row.current_price ?? "-" })] }, row.id))), pageItems.length === 0 && (_jsx("tr", { children: _jsx("td", { colSpan: 7, style: { paddingTop: 12 }, children: "\u041F\u043E \u0432\u044B\u0431\u0440\u0430\u043D\u043D\u044B\u043C \u0444\u0438\u043B\u044C\u0442\u0440\u0430\u043C \u043D\u0438\u0447\u0435\u0433\u043E \u043D\u0435 \u043D\u0430\u0439\u0434\u0435\u043D\u043E." }) }))] })] }), _jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12, gap: 12 }, children: [_jsxs("div", { children: ["\u041F\u043E\u043A\u0430\u0437\u0430\u043D\u043E ", pageItems.length, " \u0438\u0437 ", filteredItems.length] }), _jsxs("div", { style: { display: "flex", gap: 8, alignItems: "center" }, children: [_jsx("button", { type: "button", onClick: () => goToPage(page - 1), disabled: page <= 1, children: "\u041D\u0430\u0437\u0430\u0434" }), _jsxs("span", { children: ["\u0421\u0442\u0440\u0430\u043D\u0438\u0446\u0430 ", page, " / ", totalPages] }), _jsx("button", { type: "button", onClick: () => goToPage(page + 1), disabled: page >= totalPages, children: "\u0412\u043F\u0435\u0440\u0435\u0434" })] })] })] }));
}
