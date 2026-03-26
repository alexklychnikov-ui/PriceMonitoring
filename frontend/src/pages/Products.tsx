import { useEffect, useMemo, useState, type ChangeEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useProducts } from "../hooks/useProducts";

type ProductFilters = {
  name: string;
  brand: string;
  season: "all" | "winter" | "summer";
  tireSize: string;
  radius: string;
  spike: "all" | "yes" | "no";
  minPrice: string;
  maxPrice: string;
};

const STORAGE_KEY = "products-filters-v2";
const PAGE_SIZE = 20;

const EMPTY_FILTERS: ProductFilters = {
  name: "",
  brand: "",
  season: "all",
  tireSize: "",
  radius: "",
  spike: "all",
  minPrice: "",
  maxPrice: "",
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

export function ProductsPage() {
  const { data, isLoading } = useProducts();
  const navigate = useNavigate();
  const [filters, setFilters] = useState<ProductFilters>(loadSavedFilters);
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
      const tireSizeMatches = (item.tire_size ?? "").toLowerCase().includes(tireSizeNeedle);
      const radiusMatches = (item.radius ?? "").toLowerCase().includes(radiusNeedle);
      const spikeMatches =
        filters.spike === "all" || (filters.spike === "yes" && item.spike === true) || (filters.spike === "no" && item.spike === false);
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
    setPage(1);
  };

  if (isLoading) {
    return <div className="card">Загрузка...</div>;
  }

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 8 }}>
        <h3 style={{ margin: 0 }}>Каталог товаров</h3>
        <button type="button" onClick={resetAllFilters}>
          Сброс всех фильтров
        </button>
      </div>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th align="left">Название</th>
            <th align="left">Бренд</th>
            <th align="left">Сезон</th>
            <th align="left">Размер</th>
            <th align="left">Радиус</th>
            <th align="left">Шипы</th>
            <th align="left">Цена</th>
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
          </tr>
        </thead>
        <tbody>
          {pageItems.map((row) => (
            <tr key={row.id} onClick={() => navigate(`/products/${row.id}`)} style={{ cursor: "pointer" }}>
              <td>{row.name}</td>
              <td>{row.brand}</td>
              <td>{row.season ?? "-"}</td>
              <td>{row.tire_size}</td>
              <td>{row.radius}</td>
              <td>{row.spike == null ? "-" : row.spike ? "Да" : "Нет"}</td>
              <td>{row.current_price ?? "-"}</td>
            </tr>
          ))}
          {pageItems.length === 0 && (
            <tr>
              <td colSpan={7} style={{ paddingTop: 12 }}>
                По выбранным фильтрам ничего не найдено.
              </td>
            </tr>
          )}
        </tbody>
      </table>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12, gap: 12 }}>
        <div>
          Показано {pageItems.length} из {filteredItems.length}
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
