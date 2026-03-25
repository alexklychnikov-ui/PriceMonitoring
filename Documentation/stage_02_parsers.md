# Этап 2: Разработка парсеров — Мета-промпт для Cursor

## Контекст проекта

Продолжение разработки системы мониторинга цен на шины в Иркутске.
Этап 1 уже выполнен: есть схема БД, модели SQLAlchemy 2.0, конфиг.
Стек парсеров: Python 3.11+, `aiohttp` + `asyncio`, `BeautifulSoup4`, `lxml`, `fake-useragent`, ротация прокси.

## Задача для Cursor

Сгенерируй промпт для AI-ассистента редактора Cursor, который создаст модульную систему парсеров.

### Архитектура парсеров

Каждый парсер — класс, наследующийся от абстрактного `BaseScraper`:

```python
# scrapers/base.py
class BaseScraper(ABC):
    site_name: str
    base_url: str
    catalog_url: str

    async def fetch_page(self, url: str, session: aiohttp.ClientSession) -> str: ...
    async def parse_products(self, html: str) -> list[ProductDTO]: ...
    async def get_pagination_urls(self, html: str, base_url: str) -> list[str]: ...
    async def run(self) -> list[ProductDTO]: ...
```

`ProductDTO` — dataclass/Pydantic модель:
```python
class ProductDTO(BaseModel):
    external_id: str          # уникальный id товара на сайте
    name: str
    brand: str
    model: str
    season: str               # winter/summer/allseason
    tire_size: str            # '175/65' — сочетание ширина/профиль для отображения
    radius: str               # 'R14' — диаметр диска в человеческом формате
    width: int                # 175 — численная ширина для фильтрации
    profile: int              # 65 — численный профиль для фильтрации
    diameter: int             # 14 — численный диаметр для фильтрации
    price: float
    old_price: float | None
    discount_pct: float | None
    in_stock: bool
    url: str
    site_name: str
```

**Правило разбора размера шины из названия:**
Строка вида "Yokohama IG55 175/65R14 86T" разбирается так:
- `brand` = "Yokohama"
- `model` = "IG55"
- `tire_size` = "175/65" (ширина/профиль, всё до `R`)
- `radius` = "R14" (включая букву R)
- `width` = 175, `profile` = 65, `diameter` = 14 (числа для фильтрации в БД)

### Парсеры для реализации

**1. `scrapers/avtoshina38.py` — Авто-Шина 38**
- URL: `https://avtoshina38.ru/catalog/tires/`
- Защита: кастомный JS-challenge. Использовать `playwright-async` + headless Chromium для первого запроса, получить сессионные cookies, затем использовать aiohttp с этими cookies
- Структура страницы: иерархия бренд → сезон → модель → SKU (таблица `<tr>`)
- Цена: `td:nth-child(4)` — текст вида "5 599.81 ₽" (убрать пробелы, взять float)
- Старая цена: `td:nth-child(4) del` или `s` тег
- Название: `td:nth-child(3) a` — вида "Зимняя шина шип Yokohama IG55 175/65R14 86T"
- Парсить размер из названия regex: `(\d{3})/(\d{2,3})(R\d{2})`
  - `tire_size` = `f"{match.group(1)}/{match.group(2)}"` ("175/65")
  - `radius` = `match.group(3)` ("R14")
  - `width`, `profile`, `diameter` = числа из тех же групп
- AJAX "Показать ещё": POST запрос на тот же URL с параметром `PAGEN_1`

**2. `scrapers/shinservice.py` — ШинСервис**
- URL: `https://irkutsk.shinservice.ru/catalog/tyres/`
- Защита: нет
- Структура: `.product-card`
- Цена: `.product-card__price` (очистить от "₽", пробелов)
- Заголовок: `.product-card__title`
- Пагинация: `?page=N` — инкрементировать до пустой страницы

**3. `scrapers/shinapoint.py` — ШинаПоинт (Bitrix)**
- URL: `https://shinapoint.ru/catalog/tires/`
- Защита: нет
- Структура: `.catalog_item.main_item_wrapper`
- Цена: `.price_matrix_wrapper .price_value`
- Заголовок: `.item-title .item_title_span`
- Пагинация: `?PAGEN_1=N`

**4. `scrapers/ship_ship.py` — Шип-Шип**
- URL: `https://irkutsk.ship-ship.ru/tyres/`
- Защита: нет
- Структура: `.product-card`
- Цена: `.product-card__price-value`
- Заголовок: `.product-card__title`
- Пагинация: `?PAGEN_1=N`

**5. `scrapers/supershina38.py` — СуперШина**
- URL: `https://supershina38.ru/tires/`
- Защита: нет
- Структура: `div.makes_list a` (бренды) → `table tr` (размеры)
- Иерархия: `/tires/brand/{brand}/{model}` — парсить все модели всех брендов
- Цена: `td:nth-child(4)` на странице модели

**6. `scrapers/express_shina.py` — Express-Шина**
- URL: `https://irkutsk.express-shina.ru/search/legkovyie-shinyi`
- Защита: нет
- Структура: `div.b-offer`
- Цена: `.b-offer-pay__price span`
- Заголовок: `.b-offer-main__title`
- Пагинация: `?num=N`

**7. `scrapers/kolesa_darom.py` — Колёса Даром**
- URL: `https://irkutsk.kolesa-darom.ru`
- Парсить API если доступно (проверить XHR в DevTools)
- Использовать стандартный подход: catalog → product cards

### Общие требования

**`scrapers/utils.py`** — утилиты:
```python
from dataclasses import dataclass

@dataclass
class TireSizeResult:
    tire_size: str    # '205/60'
    radius: str       # 'R16'
    width: int        # 205
    profile: int      # 60
    diameter: int     # 16

def parse_tire_size(name: str) -> TireSizeResult | None:
    """
    Извлечь все составляющие размера шины из строки названия.
    Пример: '205/60R16' → TireSizeResult(tire_size='205/60', radius='R16', width=205, profile=60, diameter=16)
    Поддерживаемые форматы: '205/60R16', '205/60 R16', '205/60r16'
    """
    import re
    m = re.search(r'(\d{3})/(\d{2,3})\s*(R)(\d{2})', name, re.IGNORECASE)
    if not m:
        return None
    width, profile, diameter = int(m.group(1)), int(m.group(2)), int(m.group(4))
    return TireSizeResult(
        tire_size=f"{width}/{profile}",
        radius=f"R{diameter}",
        width=width,
        profile=profile,
        diameter=diameter,
    )

def clean_price(raw: str) -> float | None:
    """'5 599.81 ₽' → 5599.81"""

def detect_season(name: str) -> str:
    """'Зимняя шина шип...' → 'winter'"""

async def get_random_ua() -> str:
    """Случайный User-Agent"""
```

**`scrapers/proxy_manager.py`**:
```python
class ProxyManager:
    def __init__(self, proxy_list: list[str]): ...
    async def get_proxy(self) -> str: ...      # round-robin
    async def mark_failed(self, proxy: str): ...  # временно исключить
    async def health_check(self): ...           # проверять каждые 5 мин
```

**`scrapers/db_writer.py`**:
- `async def upsert_product(session, dto: ProductDTO, site_id: int) -> Product`
  - INSERT OR UPDATE по `(site_id, external_id)`
  - Всегда добавлять запись в `price_history`
  - Если цена изменилась — создавать запись в `alerts`

### Обработка ошибок

- `aiohttp.ClientError` → retry 3 раза с exponential backoff (1s, 2s, 4s)
- HTTP 429 → ждать `Retry-After` заголовок или 60 секунд
- HTTP 403 → сменить прокси, retry
- `asyncio.TimeoutError` → timeout 30 секунд на запрос
- Логировать все ошибки с `site_name`, `url`, `error_type`

### Тесты

Создать `tests/test_parsers.py`:
- Тест для каждого `parse_products()` с HTML-фикстурой из файла
- Тест `parse_tire_size()` с разными форматами строк
- Тест `clean_price()` с граничными случаями

## Требования к генерируемому Cursor-промпту

- Создавать файлы строго в указанном порядке: base → utils → proxy_manager → конкретные парсеры → db_writer → тесты
- Использовать только async/await, никаких sync HTTP запросов
- Каждый парсер должен иметь `__main__` блок для независимого тестирования: `asyncio.run(ScraperName().run())`
- Добавить `scrapers/__init__.py` с `SCRAPERS_REGISTRY: dict[str, type[BaseScraper]]`
- requirements.txt должен включать: aiohttp, beautifulsoup4, lxml, playwright, fake-useragent, pydantic, sqlalchemy[asyncio], asyncpg, python-dotenv
