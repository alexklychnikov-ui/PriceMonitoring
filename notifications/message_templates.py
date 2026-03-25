from __future__ import annotations

from jinja2 import Environment


PRICE_DROP_TEMPLATE = """
🟢 *Снижение цены\!*

🏪 Магазин: {{ site_name }}
🔖 Товар: {{ product_name }}
📐 Размер: {{ size }}

💰 Было: ~~{{ old_price|format_rub }}~~
💰 Стало: *{{ new_price|format_rub }}*
📉 Снижение: -{{ change_pct }}%
💵 Экономия: {{ savings|format_rub }}

🔗 [Перейти к товару]({{ product_url }})
"""

PRICE_RISE_TEMPLATE = """
🔴 *Рост цены*

🏪 {{ site_name }} | {{ product_name }} ({{ size }})
📈 {{ old_price|format_rub }} → {{ new_price|format_rub }} (+{{ change_pct }}%)
"""

WEEKLY_DIGEST_TEMPLATE = """
📊 *Еженедельный отчет по рынку шин Иркутска*
📅 {{ week_range }}

📌 *Ключевые цифры:*
• Отслежено изменений: {{ total_changes }}
• Средняя динамика: {{ avg_change }}%
• Лучшие скидки недели: {{ top_deals_count }} позиций

🏆 *Топ снижений:*
{% for deal in top_deals %}
{{ loop.index }}. {{ deal.name }} — {{ deal.new_price|format_rub }} (-{{ deal.change_pct }}%)
{% endfor %}

💡 {{ ai_recommendation }}
"""


def _format_rub(value: float | int | str) -> str:
    amount = float(value)
    return f"{amount:,.0f}".replace(",", " ") + " ₽"


env = Environment(autoescape=False, trim_blocks=True, lstrip_blocks=True)
env.filters["format_rub"] = _format_rub


def render_template(template: str, **kwargs) -> str:
    return env.from_string(template).render(**kwargs)
