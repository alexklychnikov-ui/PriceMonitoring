# Этап 5: Frontend-дашборд — Мета-промпт для Cursor

## Контекст проекта

Система мониторинга цен на шины в Иркутске. Этапы 1-4 выполнены.
Есть: полная бэкенд-система с API, данные в PostgreSQL, AI-анализ.
Задача: создать FastAPI backend API + React frontend дашборд.
Стек: **FastAPI**, **React 18**, **Recharts** (графики), **TanStack Table**, **Tailwind CSS**, **Vite**.

## Задача для Cursor

Сгенерируй промпт для AI-ассистента редактора Cursor, который создаст полный дашборд.

### Backend API (`api/`)

**`api/main.py`** — FastAPI приложение:
```python
app = FastAPI(title="Price Monitor API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"])

# Подключить роутеры:
app.include_router(products_router, prefix="/api/products")
app.include_router(sites_router, prefix="/api/sites")
app.include_router(analytics_router, prefix="/api/analytics")
app.include_router(settings_router, prefix="/api/settings")
```

**`api/routers/products.py`**:
```python
GET  /api/products                  # список с фильтрами и пагинацией
GET  /api/products/{id}             # детальная карточка товара
GET  /api/products/{id}/history     # история цен (для графика)
GET  /api/products/{id}/compare     # сравнение цен по сайтам
GET  /api/products/search           # полнотекстовый поиск
```

Параметры для GET /api/products:
- `brand: str | None`
- `season: str | None` (winter/summer/allseason)
- `width, profile, diameter: int | None`
- `site_name: str | None`
- `price_min, price_max: float | None`
- `sort_by: str = "price"` (price / price_change / name)
- `tire_size: str | None` (например "175/65")
- `radius: str | None` (например "R14")
- `sort_order: str = "asc"`
- `page: int = 1`, `page_size: int = 50`

**`api/routers/analytics.py`**:
```python
GET  /api/analytics/overview        # общая статистика (cards на главной)
GET  /api/analytics/price-changes   # изменения цен за период
GET  /api/analytics/best-deals      # лучшие предложения
GET  /api/analytics/weekly-report   # AI weekly report из Redis
GET  /api/analytics/site-stats      # статистика по сайтам
```

**`api/routers/settings.py`**:
```python
GET  /api/settings/sites            # список сайтов с настройками
PUT  /api/settings/sites/{id}       # включить/выключить сайт
POST /api/settings/scrape-now/{site_name}  # ручной запуск парсинга
GET  /api/settings/alert-rules      # правила алертов
POST /api/settings/alert-rules      # создать правило
DELETE /api/settings/alert-rules/{id}
```

### Frontend структура (`frontend/`)

```
frontend/
├── src/
│   ├── components/
│   │   ├── layout/           # Sidebar, Header, Layout
│   │   ├── charts/           # PriceHistoryChart, SiteComparisonChart
│   │   ├── tables/           # ProductsTable, PriceChangesTable
│   │   ├── cards/            # StatCard, ProductCard, AlertCard
│   │   └── ui/               # Button, Badge, Spinner, Modal (shadcn/ui или самописные)
│   ├── pages/
│   │   ├── Dashboard.tsx     # главная страница
│   │   ├── Products.tsx      # каталог с фильтрами
│   │   ├── ProductDetail.tsx # карточка товара с графиком
│   │   ├── Analytics.tsx     # аналитика и отчёты
│   │   └── Settings.tsx      # настройки парсинга
│   ├── hooks/
│   │   ├── useProducts.ts    # React Query hook для товаров
│   │   ├── useAnalytics.ts   # hook для аналитики
│   │   └── useSettings.ts    # hook для настроек
│   ├── api/
│   │   └── client.ts         # axios instance + все API функции
│   └── types/
│       └── index.ts          # TypeScript типы (Product, PriceHistory, Site, etc.)
```

### Dashboard.tsx — главная страница

**Карточки статистики (верхний ряд):**
- Всего товаров в мониторинге: число с иконкой
- Отслеживается сайтов: X из 7 активных
- Изменений цен за 24ч: число (зелёный если снижений больше)
- Непрочитанных алертов: число с badge

**График — PriceChangesChart:**
- Line chart (Recharts `LineChart`) — динамика средних цен по дням
- X-ось: дата (последние 30 дней)
- Y-ось: цена в ₽
- По одной линии на каждый сайт (7 линий, разные цвета)
- Tooltip при наведении показывает все цены на дату

**Таблица — Последние изменения цен (10 записей):**
- Колонки: Товар, Сайт, Старая цена, Новая цена, Изменение (% со стрелкой)
- Строки с падением — зелёный фон, с ростом — красный

**Блок — Лучшие предложения (Best Deals):**
- 5 карточек товаров с наибольшей скидкой прямо сейчас
- Карточка: фото (если есть), название, цена, % скидки, кнопка "Перейти"

### Products.tsx — каталог

**Боковая панель фильтров:**
```
Бренд: [мультиселект с поиском]
Сезон: [Зимние / Летние / Всесезонные]
Размер (ширина/профиль): [tire_size: выпадающий, например "175/65"]
Радиус: [radius: выпадающий, например "R14", "R15", "R16"]
Ширина (число): [выпадающий: 155, 165, 175, 185, 195, 205, 215, 225...]
Профиль (число): [выпадающий: 45, 50, 55, 60, 65, 70...]
Цена: [слайдер min-max от 0 до 50000 ₽]
Магазин: [чекбоксы все 7 сайтов]
```

**Таблица товаров (TanStack Table):**
- Колонки: Название, Бренд, Размер (tire_size), Радиус (radius), Сезон, Мин. цена, Макс. цена, Разброс %, Обновлено
- Сортировка по колонкам (клик на заголовок)
- Пагинация: 50 записей на страницу
- Клик на строку → переход на ProductDetail.tsx

### ProductDetail.tsx — карточка товара

**Верхняя часть:**
- Полное название товара
- Badges: бренд, сезон (иконки снежинка/солнце), размер

**График истории цен:**
- Area chart (Recharts) — история цены за 30 дней по каждому сайту
- Переключатель периода: 7 дней / 30 дней / 90 дней
- При hover — tooltip с ценами по сайтам

**Сравнение цен по сайтам (таблица):**
- Строки: название сайта, текущая цена, дата обновления, ссылка
- Минимальная цена выделена зелёным

**AI-рекомендация (блок):**
- Загружает `/api/products/{id}/ai-analysis`
- Skeleton-loader пока грузится
- Отображает текст рекомендации от LLM

### Settings.tsx — настройки

- Таблица сайтов с тоглом вкл/выкл
- Кнопка "Запустить парсинг сейчас" для каждого сайта
- Статус последнего парсинга (success/failed/running с иконкой)
- Форма создания правила алерта:
  - Тип: снижение цены / рост цены
  - Порог в %
  - Бренд/модель (опционально)

## Требования к генерируемому Cursor-промпту

- Использовать **React Query (TanStack Query v5)** для всех API запросов (кэширование, loading states)
- Все числа форматировать с `Intl.NumberFormat('ru-RU', {style: 'currency', currency: 'RUB'})`
- Цветовая схема: тёмная тема (#0f172a фон, #1e293b карточки, зелёный #22c55e снижение, красный #ef4444 рост)
- TypeScript строгий режим (`strict: true`)
- `vite.config.ts` с proxy на FastAPI: `/api` → `http://localhost:8000`
- Добавить `README.md` с инструкцией запуска: `npm install && npm run dev`
- FastAPI: включить автодокументацию Swagger на `/docs`
