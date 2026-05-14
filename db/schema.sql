-- db/schema.sql
-- Applied automatically by load.py on every run (all statements are idempotent).
-- Can also be applied manually:
--   psql -U $DB_USER -d $DB_NAME -f db/schema.sql

-- ── Fact table ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS gdp_data (
    id              SERIAL PRIMARY KEY,
    country         TEXT           NOT NULL,
    iso3_code       CHAR(3),
    year            INTEGER        NOT NULL,
    gdp_per_capita  NUMERIC(18, 4) NOT NULL,
    income_group    TEXT,
    source          TEXT           NOT NULL DEFAULT 'World Bank',
    created_at      TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    UNIQUE (country, year)
);

-- ── Migrations: add new columns to existing tables safely ─────────────────────
-- ADD COLUMN IF NOT EXISTS is idempotent — skipped silently if already present.
ALTER TABLE gdp_data ADD COLUMN IF NOT EXISTS iso3_code   CHAR(3);
ALTER TABLE gdp_data ADD COLUMN IF NOT EXISTS income_group TEXT;

-- ── Indexes ───────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_gdp_country ON gdp_data(country);
CREATE INDEX IF NOT EXISTS idx_gdp_year    ON gdp_data(year);
CREATE INDEX IF NOT EXISTS idx_gdp_income  ON gdp_data(income_group);

-- ── Views ─────────────────────────────────────────────────────────────────────
-- DROP with CASCADE removes this view and anything that depends on it
-- (gdp_income_summary, gdp_regional_stats, or any other derived view).
-- Views contain no data so this is always safe.
DROP VIEW IF EXISTS gdp_latest CASCADE;

CREATE VIEW gdp_latest AS
SELECT DISTINCT ON (country)
    id,
    country,
    iso3_code,
    year,
    gdp_per_capita,
    income_group,
    source,
    updated_at
FROM gdp_data
ORDER BY country, year DESC;

CREATE VIEW gdp_income_summary AS
SELECT
    income_group,
    COUNT(*)                                  AS country_count,
    ROUND(AVG(gdp_per_capita)::NUMERIC, 2)   AS avg_gdp_per_capita,
    ROUND(MIN(gdp_per_capita)::NUMERIC, 2)   AS min_gdp_per_capita,
    ROUND(MAX(gdp_per_capita)::NUMERIC, 2)   AS max_gdp_per_capita
FROM gdp_latest
GROUP BY income_group
ORDER BY avg_gdp_per_capita DESC;

CREATE VIEW gdp_regional_stats AS
SELECT
    income_group,
    COUNT(*)                                    AS country_count,
    ROUND(AVG(gdp_per_capita)::NUMERIC, 2)     AS avg_gdp,
    ROUND(MIN(gdp_per_capita)::NUMERIC, 2)     AS min_gdp,
    ROUND(MAX(gdp_per_capita)::NUMERIC, 2)     AS max_gdp,
    ROUND(STDDEV(gdp_per_capita)::NUMERIC, 2)  AS stddev_gdp
FROM gdp_latest
GROUP BY income_group
ORDER BY avg_gdp DESC;