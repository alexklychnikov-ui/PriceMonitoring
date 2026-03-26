CREATE TABLE IF NOT EXISTS sites (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    base_url TEXT NOT NULL,
    catalog_url TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS products (
    id BIGSERIAL PRIMARY KEY,
    site_id BIGINT NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    external_id VARCHAR(255) NOT NULL,
    name TEXT NOT NULL,
    brand VARCHAR(255),
    model VARCHAR(255),
    season VARCHAR(32),
    spike BOOLEAN,
    tire_size VARCHAR(10),
    radius VARCHAR(5),
    width INT,
    profile INT,
    diameter INT,
    url TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_products_site_external UNIQUE (site_id, external_id)
);

CREATE TABLE IF NOT EXISTS price_history (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    price NUMERIC(12, 2) NOT NULL,
    old_price NUMERIC(12, 2),
    discount_pct NUMERIC(5, 2),
    in_stock BOOLEAN NOT NULL DEFAULT TRUE,
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS parse_runs (
    id BIGSERIAL PRIMARY KEY,
    site_id BIGINT REFERENCES sites(id) ON DELETE SET NULL,
    status VARCHAR(32) NOT NULL,
    trigger_type VARCHAR(32) NOT NULL DEFAULT 'scheduled',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    products_found INT NOT NULL DEFAULT 0,
    errors_count INT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS alerts (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    alert_type VARCHAR(64) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS user_subscriptions (
    id BIGSERIAL PRIMARY KEY,
    chat_id VARCHAR(50) NOT NULL,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    threshold_pct NUMERIC(5, 2) NOT NULL DEFAULT 5.0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_subscriptions_chat_product UNIQUE (chat_id, product_id)
);

CREATE TABLE IF NOT EXISTS alert_rules (
    id BIGSERIAL PRIMARY KEY,
    rule_type VARCHAR(32) NOT NULL,
    threshold_pct NUMERIC(5, 2) NOT NULL DEFAULT 5.0,
    brand VARCHAR(255),
    season VARCHAR(32),
    site_name VARCHAR(255),
    chat_id VARCHAR(50) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_price_history_product_scraped_at
    ON price_history (product_id, scraped_at DESC);

CREATE INDEX IF NOT EXISTS idx_products_brand_tire_size_radius
    ON products (brand, tire_size, radius);

CREATE INDEX IF NOT EXISTS idx_products_tire_size_radius
    ON products (tire_size, radius);

CREATE INDEX IF NOT EXISTS idx_products_site_name_size_diameter
    ON products (site_id, name, tire_size, diameter);

CREATE INDEX IF NOT EXISTS idx_subscriptions_product_active
    ON user_subscriptions (product_id, is_active);
