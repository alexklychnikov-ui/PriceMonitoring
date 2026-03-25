# Этап 4: AI-анализ цен — Мета-промпт для Cursor

## Контекст проекта

Система мониторинга цен на шины в Иркутске. Этапы 1-3 выполнены.
Есть: БД с `price_history`, работающий планировщик, Redis.
Задача этапа: добавить AI-слой анализа поверх накопленных данных.
Стек: **LangChain 0.2+**, **OpenAI API** (или локальный **Ollama**), **pandas**, **NumPy**.

## Задача для Cursor

Сгенерируй промпт для AI-ассистента редактора Cursor, который создаст модуль AI-аналитики.

### Структура файлов

```
ai_analysis/
├── __init__.py
├── price_analyzer.py       # анализ ценовых трендов
├── recommendation_engine.py # генерация рекомендаций
├── prompts.py              # все LLM промпты
├── tools.py                # LangChain tools для агента
└── reports.py              # форматирование отчётов
```

### `ai_analysis/price_analyzer.py`

```python
class PriceAnalyzer:
    async def get_price_history_df(
        self,
        product_id: int | None = None,
        brand: str | None = None,
        days: int = 30
    ) -> pd.DataFrame:
        """Загрузить историю цен в DataFrame:
        Колонки: scraped_at, site_name, brand, model, size, price, old_price
        """

    def calculate_trends(self, df: pd.DataFrame) -> dict:
        """
        Возвращает:
        - min_price, max_price, avg_price, current_price
        - price_change_7d_pct: изменение за 7 дней в %
        - price_change_30d_pct: изменение за 30 дней в %
        - volatility: std / mean
        - trend_direction: "rising" / "falling" / "stable"
        - cheapest_site: сайт с минимальной текущей ценой
        - price_spread: (max - min) / min * 100 — разброс между сайтами
        """

    def find_price_anomalies(self, df: pd.DataFrame) -> list[dict]:
        """
        Найти аномальные изменения цен:
        - Снижение > 20% за 1 день (возможная акция или ошибка)
        - Рост > 30% за 1 день
        - Цена ниже среднего по рынку на 30%+
        Использовать Z-score или IQR метод
        """

    def compare_sites(self, brand: str, model: str, size: str) -> pd.DataFrame:
        """
        Сравнить цены на одинаковый товар (brand+model+size) по всем 7 сайтам.
        Возвращает DataFrame: site_name, current_price, last_updated, url
        Отсортированный по цене.
        """
```

### `ai_analysis/prompts.py`

Создать шаблоны промптов каждый в отдельном файле для разных задач:

```python
PRICE_TREND_ANALYSIS_PROMPT = """
Ты эксперт по рынку автомобильных шин в Иркутске.
Проанализируй следующие данные о ценах:

Товар: {product_name}
Бренд: {brand}, Модель: {model}, Радиус: {radius}
Период: последние {days} дней

Статистика:
- Текущая цена: {current_price} ₽
- Минимальная за период: {min_price} ₽ ({min_site})
- Максимальная за период: {max_price} ₽ ({max_site})
- Изменение за 7 дней: {change_7d}%
- Изменение за 30 дней: {change_30d}%
- Волатильность: {volatility}
- Тренд: {trend_direction}
- Разброс цен между магазинами: {price_spread}%

Цены по сайтам прямо сейчас:
{sites_comparison}

Ответь на вопросы:
1. Как ведут себя цены на этот товар? Есть ли сезонность?
2. На каком сайте сейчас выгоднее купить и почему?
3. Стоит ли покупать сейчас или подождать?
4. Есть ли признаки временной акции или манипуляции ценой?

Ответ дай структурированно, на русском языке, 3-4 предложения по каждому пункту.
"""

MARKET_OVERVIEW_PROMPT = """
Ты аналитик рынка шин в Иркутске. Составь краткий еженедельный отчёт.

Данные за последние 7 дней:
- Отслеживается сайтов: {sites_count}
- Всего товаров в мониторинге: {products_count}
- Изменений цен зафиксировано: {price_changes_count}
- Среднее снижение цен: {avg_decrease}%
- Среднее повышение цен: {avg_increase}%

Топ-5 самых подешевевших позиций:
{top_discounts}

Топ-5 самых подорожавших позиций:
{top_increases}

Составь отчёт в формате:
## Обзор рынка шин Иркутск — {week}
### Ключевые тренды
### Лучшие предложения недели
### На что обратить внимание
"""

PRICING_RECOMMENDATION_PROMPT = """
Ты консультант по ценообразованию для магазина шин в Иркутске.

Конкурентный анализ для позиции "{product_name}":
{competitor_prices}

Наша текущая цена: {our_price} ₽
Наша позиция на рынке: {our_rank} из {total_sites} магазинов

Дай рекомендацию:
1. Оптимальная цена для максимальной конверсии
2. Цена для максимальной маржи при сохранении конкурентности
3. Обоснование рекомендации (2-3 предложения)

Формат: JSON с полями optimal_price, margin_price, reasoning
"""
```

### `ai_analysis/tools.py` — LangChain Tools

```python
# Инструменты для LangChain агента

@tool
async def get_price_for_tire(brand: str, model: str, size: str) -> str:
    """Получить текущие цены на конкретную шину по всем магазинам Иркутска.
    Аргументы: brand (например 'Yokohama'), model (например 'IG55'), size (например '205/60R16')
    """

@tool
async def get_price_history(brand: str, model: str, size: str, days: int = 30) -> str:
    """Получить историю изменения цен на шину за последние N дней."""

@tool
async def get_market_overview() -> str:
    """Получить общий обзор рынка шин в Иркутске за последнюю неделю."""

@tool
async def find_best_deals(season: str = "winter", budget: float = 10000) -> str:
    """Найти лучшие предложения по шинам в рамках бюджета.
    season: 'winter', 'summer', 'allseason'
    budget: максимальная цена в рублях
    """
```

### `ai_analysis/recommendation_engine.py`

```python
class RecommendationEngine:
    def __init__(self, llm_provider: str = "openai"):
        # Поддерживать два провайдера:
        # "openai" — gpt-4o-mini через OpenAI API
        # "ollama" — llama3.2 через http://localhost:11434
        ...

    async def analyze_product_price(self, product_id: int) -> PriceAnalysisResult: ...
    async def generate_weekly_report(self) -> str: ...
    async def get_buy_recommendation(self, brand: str, model: str, size: str) -> str: ...

    # Кэшировать результаты в Redis с TTL:
    # analyze_product_price — TTL 1 час
    # generate_weekly_report — TTL 24 часа
    # get_buy_recommendation — TTL 2 часа
```

### Конфигурация LLM

В `config.py` добавить:
```python
LLM_PROVIDER: str = "openai"    # "openai" или "ollama"

# ProxyAPI — OpenAI-совместимый прокси (openai.api.proxyapi.ru)
# Используется когда LLM_PROVIDER="openai"
PROXY_API_KEY: str = ""                                          # заменяет OPENAI_API_KEY
PROXY_BASE_URL: str = "https://openai.api.proxyapi.ru/v1"       # base_url для OpenAI SDK
OPENAI_MODEL: str = "gpt-4o-mini"

# Ollama — локальная модель, используется когда LLM_PROVIDER="ollama"
OLLAMA_BASE_URL: str = "http://localhost:11434"
OLLAMA_MODEL: str = "llama3.2"
```

**Инициализация клиента LangChain через ProxyAPI:**
```python
from langchain_openai import ChatOpenAI

def get_llm() -> ChatOpenAI:
    if settings.LLM_PROVIDER == "openai":
        return ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.PROXY_API_KEY,       # ключ ProxyAPI
            base_url=settings.PROXY_BASE_URL,     # https://openai.api.proxyapi.ru/v1
        )
    else:
        from langchain_community.llms import Ollama
        return Ollama(base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL)
```

### Celery-задача в `scheduler/tasks.py` (дополнение)

```python
@app.task
async def analyze_prices_task():
    """Запускается после каждого парсинга через chord().
    1. Для каждого изменившегося товара запускает analyze_product_price()
    2. Если изменение > PRICE_ALERT_THRESHOLD_PCT — создаёт запись в alerts
    3. По воскресеньям генерирует weekly_report и сохраняет в Redis
    """
```

## Требования к генерируемому Cursor-промпту

- Все LLM вызовы обернуть в try/except с fallback на простой шаблонный ответ без AI
- Использовать `langchain_openai.ChatOpenAI` (с `api_key=PROXY_API_KEY` и `base_url=PROXY_BASE_URL`) и `langchain_community.llms.Ollama`
- Добавить `ai_analysis/cache.py` — обёртка над Redis для кэширования результатов LLM (экономия токенов)
- Промпты хранить в `prompts.py` как константы, НЕ инлайн в коде
- Добавить `tests/test_ai_analysis.py` с моками LLM (не тратить API-токены в тестах)
- Логировать количество использованных токенов для мониторинга расходов
