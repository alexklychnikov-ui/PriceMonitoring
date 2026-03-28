import { useEffect, useMemo, useState, type ChangeEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useProducts } from "../hooks/useProducts";
import type { Product } from "../types";
import { formatScraperLabel } from "../utils/siteLabel";

type ProductFilters = {
  name: string;
  brand: string;
  model: string;
  season: "all" | "winter" | "summer";
  tireSize: string;
  radius: string;
  spike: "all" | "yes" | "no";
  minPrice: string;
  maxPrice: string;
};

type SortKey = "name" | "brand" | "model" | "price" | "season" | "tire_size" | "radius" | "site_name";
type SortOrder = "asc" | "desc";

const STORAGE_KEY = "products-filters-v3";
const SHOW_UNAVAILABLE_KEY = "products-show-unavailable";
const PAGE_SIZE = 20;

const EMPTY_FILTERS: ProductFilters = {
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

const DEFAULT_SORT: { sortBy: SortKey; sortOrder: SortOrder } = {
  sortBy: "price",
  sortOrder: "asc",
};

function loadSavedFilters(): ProductFilters {
  if (typeof window === "undefined") {
    return EMPTY_FILTERS;
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return EMPTY_FILTERS;
    }
    const parsed = JSON.parse(raw) as Partial<ProductFilters>;
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
  } catch {
    return EMPTY_FILTERS;
  }
}

function loadSavedSort(): { sortBy: SortKey; sortOrder: SortOrder } {
  if (typeof window === "undefined") {
    return DEFAULT_SORT;
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return DEFAULT_SORT;
    }
    const parsed = JSON.parse(raw) as { sortBy?: string; sortOrder?: string };
    const keys: SortKey[] = ["name", "brand", "model", "price", "season", "tire_size", "radius", "site_name"];
    const sortBy = keys.includes(parsed.sortBy as SortKey) ? (parsed.sortBy as SortKey) : DEFAULT_SORT.sortBy;
    const sortOrder = parsed.sortOrder === "desc" ? "desc" : "asc";
    return { sortBy, sortOrder };
  } catch {
    return DEFAULT_SORT;
  }
}

function sortValue(p: Product, key: SortKey): string | number {
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

const SORT_COLUMNS: { key: SortKey; label: string }[] = [
  { key: "name", label: "Название" },
  { key: "brand", label: "Бренд" },
  { key: "model", label: "Модель" },
  { key: "season", label: "Сезон" },
  { key: "tire_size", label: "Размер" },
  { key: "radius", label: "Радиус" },
  { key: "site_name", label: "Парсер" },
  { key: "price", label: "Цена" },
];

function loadShowUnavailable(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  try {
    return window.localStorage.getItem(SHOW_UNAVAILABLE_KEY) === "1";
  } catch {
    return false;
  }
}

export function ProductsPage() {
  const [showUnavailable, setShowUnavailable] = useState(loadShowUnavailable);
  const { data, isLoading } = useProducts(showUnavailable);
  const navigate = useNavigate();
  const [filters, setFilters] = useState<ProductFilters>(loadSavedFilters);
  const [sortBy, setSortBy] = useState<SortKey>(() => loadSavedSort().sortBy);
  const [sortOrder, setSortOrder] = useState<SortOrder>(() => loadSavedSort().sortOrder);
  const [page, setPage] = useState(1);

  useEffect(() => {
    try {
      window.localStorage.setItem(SHOW_UNAVAILABLE_KEY, showUnavailable ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [showUnavailable]);

  useEffect(() => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ ...filters, sortBy, sortOrder }),
    );
  }, [filters, sortBy, sortOrder]);

  const filteredItems = useMemo(() => {
    const items = data?.items ?? [];
    const nameNeedle = filters.name.trim().toLowerCase();
    const brandNeedle = filters.brand.trim().toLowerCase();
    const modelNeedle = filters.model.trim().toLowerCase();
    const tireSizeNeedle = filters.tireSize.trim().toLowerCase();
    const radiusNeedle = filters.radius.trim().toLowerCase();
    const seasonMatchesFilter = (seasonValue: string | null | undefined) => {
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
      const spikeMatches =
        filters.spike === "all" || (filters.spike === "yes" && item.spike === true) || (filters.spike === "no" && item.spike === false);
      const seasonMatches = seasonMatchesFilter(item.season);
      const price = item.current_price;
      const minPriceMatches = !hasMinPrice || (price != null && price >= minPrice);
      const maxPriceMatches = !hasMaxPrice || (price != null && price <= maxPrice);
      return (
        nameMatches &&
        brandMatches &&
        modelMatches &&
        seasonMatches &&
        tireSizeMatches &&
        radiusMatches &&
        spikeMatches &&
        minPriceMatches &&
        maxPriceMatches
      );
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

  const handleFilterChange =
    (key: keyof ProductFilters) => (event: ChangeEvent<HTMLInputElement>) => {
      setFilters((prev) => ({ ...prev, [key]: event.target.value }));
      setPage(1);
    };

  const goToPage = (nextPage: number) => {
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

  const toggleSort = (key: SortKey) => {
    if (sortBy === key) {
      setSortOrder((o) => (o === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(key);
      setSortOrder(key === "price" ? "asc" : "asc");
    }
    setPage(1);
  };

  const headerArrow = (key: SortKey) => {
    if (sortBy !== key) {
      return "";
    }
    return sortOrder === "asc" ? " ↑" : " ↓";
  };

  if (isLoading) {
    return <div className="card">Загрузка...</div>;
  }

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 8, flexWrap: "wrap" }}>
        <h3 style={{ margin: 0 }}>Каталог товаров</h3>
        <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", userSelect: "none" }}>
          <input
            type="checkbox"
            checked={showUnavailable}
            onChange={(e) => {
              setShowUnavailable(e.target.checked);
              setPage(1);
            }}
          />
          Показать снятые с витрины
        </label>
        <button type="button" onClick={resetAllFilters}>
          Сброс всех фильтров
        </button>
      </div>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            {SORT_COLUMNS.map((col) => (
              <th key={col.key} align="left">
                <button
                  type="button"
                  onClick={() => toggleSort(col.key)}
                  style={{
                    background: "none",
                    border: "none",
                    padding: 0,
                    cursor: "pointer",
                    font: "inherit",
                    fontWeight: 700,
                    textAlign: "left",
                    color: "inherit",
                  }}
                  title="Сортировать"
                >
                  {col.label}
                  {headerArrow(col.key)}
                </button>
              </th>
            ))}
            <th align="left">Шипы</th>
          </tr>
          <tr>
            <th>
              <input
                value={filters.name}
                onChange={handleFilterChange("name")}
                placeholder="Фильтр названия"
                style={{ width: "100%" }}
              />
            </th>
            <th>
              <input
                value={filters.brand}
                onChange={handleFilterChange("brand")}
                placeholder="Фильтр бренда"
                style={{ width: "100%" }}
              />
            </th>
            <th>
              <input
                value={filters.model}
                onChange={handleFilterChange("model")}
                placeholder="Модель"
                style={{ width: "100%" }}
              />
            </th>
            <th>
              <select
                value={filters.season}
                onChange={(event) => {
                  setFilters((prev) => ({ ...prev, season: event.target.value as ProductFilters["season"] }));
                  setPage(1);
                }}
                style={{ width: "100%" }}
              >
                <option value="all">Все</option>
                <option value="winter">Зима</option>
                <option value="summer">Лето</option>
              </select>
            </th>
            <th>
              <input
                value={filters.tireSize}
                onChange={handleFilterChange("tireSize")}
                placeholder="Фильтр размера"
                style={{ width: "100%" }}
              />
            </th>
            <th>
              <input
                value={filters.radius}
                onChange={handleFilterChange("radius")}
                placeholder="Фильтр радиуса"
                style={{ width: "100%" }}
              />
            </th>
            <th>
              <span style={{ opacity: 0.6, fontSize: "0.85em" }}>—</span>
            </th>
            <th>
              <div style={{ display: "grid", gap: 4 }}>
                <input
                  value={filters.minPrice}
                  onChange={handleFilterChange("minPrice")}
                  placeholder="Цена от"
                  inputMode="numeric"
                  style={{ width: "100%" }}
                />
                <input
                  value={filters.maxPrice}
                  onChange={handleFilterChange("maxPrice")}
                  placeholder="Цена до"
                  inputMode="numeric"
                  style={{ width: "100%" }}
                />
              </div>
            </th>
            <th>
              <select
                value={filters.spike}
                onChange={(event) => {
                  setFilters((prev) => ({ ...prev, spike: event.target.value as ProductFilters["spike"] }));
                  setPage(1);
                }}
                style={{ width: "100%" }}
              >
                <option value="all">Все</option>
                <option value="yes">Да</option>
                <option value="no">Нет</option>
              </select>
            </th>
          </tr>
        </thead>
        <tbody>
          {pageItems.map((row) => (
            <tr key={row.id} onClick={() => navigate(`/products/${row.id}`)} style={{ cursor: "pointer" }}>
              <td>{row.name}</td>
              <td>{row.brand}</td>
              <td>{row.model ?? "—"}</td>
              <td>{row.season ?? "-"}</td>
              <td>{row.tire_size}</td>
              <td>{row.radius}</td>
              <td style={{ fontFamily: "monospace", fontSize: "0.9em" }}>{formatScraperLabel(row.site_name, row.site_id)}</td>
              <td>{row.current_price ?? "-"}</td>
              <td>{row.spike == null ? "-" : row.spike ? "Да" : "Нет"}</td>
            </tr>
          ))}
          {pageItems.length === 0 && (
            <tr>
              <td colSpan={9} style={{ paddingTop: 12 }}>
                По выбранным фильтрам ничего не найдено.
              </td>
            </tr>
          )}
        </tbody>
      </table>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12, gap: 12 }}>
        <div>
          Показано {pageItems.length} из {sortedItems.length}
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button type="button" onClick={() => goToPage(page - 1)} disabled={page <= 1}>
            Назад
          </button>
          <span>
            Страница {page} / {totalPages}
          </span>
          <button type="button" onClick={() => goToPage(page + 1)} disabled={page >= totalPages}>
            Вперед
          </button>
        </div>
      </div>
    </div>
  );
}
