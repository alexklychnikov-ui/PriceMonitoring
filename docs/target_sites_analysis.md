# Анализ целевых сайтов для парсинга

## 1) avtoshina38.ru
- Точка входа: `https://avtoshina38.ru/catalog/tires/`
- Карточка товара: `table tr`
- Название: `td:nth-child(3) a`
- Цена: `td:nth-child(4)`
- Старая цена: `td:nth-child(4) del`, `td:nth-child(4) s`
- Бренд/модель/размер: извлекаются из названия regex `(\d{3})/(\d{2,3})(R\d{2})`
- Сезон: извлекается из текста названия (`зимняя/летняя/всесезонная`)
- Пагинация: AJAX "Показать еще", POST на каталог с параметром `PAGEN_1`
- Защита: кастомный JS-challenge, первичный обход через Playwright для получения cookie
- Примеры товаров:
  - Yokohama IG55 175/65R14 — 5 599 ₽
  - Yokohama IG55 195/65R15 — 6 400 ₽
  - Yokohama IG55 215/65R16 — 8 899 ₽

## 2) shinservice.ru
- Точка входа: `https://irkutsk.shinservice.ru/catalog/tyres/`
- Карточка товара: `.product-card`
- Название: `.product-card__title`
- Цена: `.product-card__price`
- Старая цена: `.product-card__old-price` (если присутствует)
- Бренд: первое слово в заголовке
- Сезон/размер: извлекаются из заголовка regex `(\d{3})/(\d{2,3})(R\d{2})`
- Пагинация: `?page=N` (например `.../catalog/tyres/?page=2`)
- Защита: отсутствует
- Примеры товаров:
  - Nokian Autograph Eco 3 — 5 450 ₽
  - Cordiant Winter Drive — 6 300 ₽
  - Formula Ice Fr — 13 050 ₽

## 3) kolesa-darom.ru
- Точка входа: `https://irkutsk.kolesa-darom.ru/catalog/`
- Карточка товара: `.catalog-product`, `.product-card` (в зависимости от шаблона)
- Название: `.catalog-product__title`, `.product-card__title`
- Цена: `.catalog-product__price-current`, `.product-card__price-current`
- Старая цена: `.catalog-product__price-old`, `.product-card__price-old`
- Бренд/сезон/размер: извлекаются из названия и карточки
- Пагинация: URL-параметры (`?PAGEN_1=N`, `?page=N` в зависимости от раздела)
- Защита: отсутствует
- Примеры товаров:
  - Шины сегмента 3 000–50 000+ ₽ (регион Иркутск)
  - Каталог содержит легковые и SUV-позиции
  - В карточках часто есть скидка и рассрочка

## 4) shinapoint.ru
- Точка входа: `https://shinapoint.ru/catalog/tires/search/pirelli/`
- Карточка товара: `.catalog_item.main_item_wrapper`
- Название: `.item-title .item_title_span`
- Цена: `.price_matrix_wrapper .price_value`
- Старая цена: `.price_matrix_wrapper .price.old`, `.price.old`
- Бренд: по названию/крошкам каталога
- Сезон/размер: по названию regex `(\d{3})/(\d{2,3})(R\d{2})`
- Пагинация: `?PAGEN_1=N` (например `.../?PAGEN_1=2`)
- Защита: отсутствует (Bitrix CMS)
- Примеры товаров:
  - Pirelli Ice Zero Friction 3 265/65R17 — 17 840 ₽
  - Pirelli Ice Zero Friction 3 225/45R18 — 22 450 ₽
  - Каталог включает шипованные и нешипованные модели

## 5) ship-ship.ru
- Точка входа: `https://irkutsk.ship-ship.ru/tyres/`
- Карточка товара: `.product-card`
- Название: `.product-card__title`
- Цена: `.product-card__price-value`
- Старая цена: `.product-card__price-old` (если есть)
- Бренд: первое слово в названии
- Сезон/размер: из названия regex `(\d{3})/(\d{2,3})(R\d{2})`
- Пагинация: `?PAGEN_1=N`
- Защита: отсутствует
- Примеры товаров:
  - Ovation VI-786 155/65R13 — 2 451 ₽
  - LingLong 155/70R13 — 2 458 ₽
  - В каталоге присутствуют бюджетные модели

## 6) supershina38.ru
- Точка входа: `https://supershina38.ru/tires`
- Карточка товара: `table tr`
- Название: `td:nth-child(2) a`, `td:nth-child(3) a` (зависит от страницы)
- Цена: `td:nth-child(4)`
- Старая цена: `td:nth-child(4) del`, `td:nth-child(4) s`
- Бренд/модель: из структуры бренд -> модель
- Сезон/размер: из названия regex `(\d{3})/(\d{2,3})(R\d{2})`
- Пагинация: иерархичная навигация по брендам/моделям
- Защита: отсутствует
- Примеры товаров:
  - Aplus A609 205/60R16 — 3 590 ₽
  - Aplus A701 175/65R14 — 2 800 ₽
  - Каталог содержит разные типоразмеры в табличном виде

## 7) express-shina.ru
- Точка входа: `https://irkutsk.express-shina.ru/search/legkovyie-shinyi`
- Карточка товара: `div.b-offer`
- Название: `.b-offer-main__title`
- Цена: `.b-offer-pay__price span`
- Старая цена: `.b-offer-pay__old-price`, `.old-price`
- Бренд: первое слово в названии
- Сезон/размер: из названия regex `(\d{3})/(\d{2,3})(R\d{2})`
- Пагинация: `?num=N` (например `.../search/legkovyie-shinyi?num=2`)
- Защита: отсутствует
- Примеры товаров:
  - Кама Евро 519 185/60R14 — 3 085 ₽
  - Nexen WH62 195/55R15 — 4 990 ₽
  - Matador MP-30 205/60R16 — 6 035 ₽
