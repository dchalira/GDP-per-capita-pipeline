-- ── Summary KPIs ──────────────────────────────────────────────────────────

Total Economies =
COUNTROWS( gdp_latest )

Global Avg GDP per Capita =
AVERAGEX( gdp_latest, gdp_latest[gdp_per_capita] )

Highest GDP per Capita =
MAXX( gdp_latest, gdp_latest[gdp_per_capita] )

Lowest GDP per Capita =
MINX( gdp_latest, gdp_latest[gdp_per_capita] )

-- ── Income group share ────────────────────────────────────────────────────

GDP Share % =
DIVIDE(
    SUMX( gdp_latest, gdp_latest[gdp_per_capita] ),
    CALCULATE( SUMX( ALL(gdp_latest), gdp_latest[gdp_per_capita] ) ),
    0
)

-- ── Ranking ───────────────────────────────────────────────────────────────

Country Rank =
RANKX(
    ALL( gdp_latest[country] ),
    CALCULATE( SUM( gdp_latest[gdp_per_capita] ) ),
    ,
    DESC,
    Dense
)

-- ── Inequality: ratio of top-10% avg to bottom-10% avg ───────────────────

Top 10% Avg =
VAR top_threshold =
    PERCENTILE.INC( gdp_latest[gdp_per_capita], 0.9 )
RETURN
    CALCULATE(
        AVERAGE( gdp_latest[gdp_per_capita] ),
        gdp_latest[gdp_per_capita] >= top_threshold
    )

Bottom 10% Avg =
VAR bot_threshold =
    PERCENTILE.INC( gdp_latest[gdp_per_capita], 0.1 )
RETURN
    CALCULATE(
        AVERAGE( gdp_latest[gdp_per_capita] ),
        gdp_latest[gdp_per_capita] <= bot_threshold
    )

Inequality Ratio =
DIVIDE( [Top 10% Avg], [Bottom 10% Avg], 0 )

-- ── YoY change (only relevant when multi-year data is loaded) ─────────────

GDP YoY Change % =
VAR current_year = MAX( gdp_data[year] )
VAR current_val  = CALCULATE( SUM( gdp_data[gdp_per_capita] ), gdp_data[year] = current_year )
VAR prior_val    = CALCULATE( SUM( gdp_data[gdp_per_capita] ), gdp_data[year] = current_year - 1 )
RETURN
    DIVIDE( current_val - prior_val, prior_val, BLANK() )