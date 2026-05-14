"""
app/load.py — Extract and load GDP per capita data into PostgreSQL.

Fixes applied vs original:
  1. income_group calculated and loaded (was always NULL)
  2. Table name aligned to schema.sql  →  'gdp_data'
  3. if_exists="replace" → proper upsert (replace drops views on every run)
  4. Schema executed as a single string, not split on ';'
"""

import logging
import sys
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from sqlalchemy import create_engine, text
from urllib3.util.retry import Retry

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.config import DATABASE_URL

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Extraction config ─────────────────────────────────────────────────────────
RETRY_TOTAL = 3
RETRY_BACKOFF = 1

# ── World Bank Atlas income thresholds (FY2024, GNI per capita USD) ───────────
# https://datahelpdesk.worldbank.org/knowledgebase/articles/906519
# GDP per capita (current USD) is used as a proxy — close enough for dashboards.
_INCOME_THRESHOLDS = [
    (1_135,  "Low income"),
    (4_465,  "Lower-middle income"),
    (13_845, "Upper-middle income"),
]

def _assign_income_group(gdp: float) -> str:
    """Return the World Bank income group label for a given GDP per capita value."""
    for threshold, label in _INCOME_THRESHOLDS:
        if gdp <= threshold:
            return label
    return "High income"


# ─────────────────────────────────────────────────────────────────────────────
# EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

def fetch_indicator(indicator_code: str, column_name: str) -> pd.DataFrame:
    """Fetch a single World Bank indicator with automatic retries."""
    url = (
        f"https://api.worldbank.org/v2/country/all/indicator/{indicator_code}"
        f"?format=json&per_page=5000"
    )

    session = requests.Session()
    retries = Retry(
        total=RETRY_TOTAL,
        backoff_factor=RETRY_BACKOFF,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        records = data[1] if len(data) > 1 and isinstance(data[1], list) else []

        df = pd.DataFrame(records)
        if df.empty:
            return df

        df = df[["country", "countryiso3code", "date", "value"]].copy()
        df["country"]         = df["country"].apply(
            lambda x: x["value"] if isinstance(x, dict) else x
        )
        df["countryiso3code"] = df["countryiso3code"].fillna("").str.strip()
        df.rename(columns={"countryiso3code": "iso3_code", "date": "year", "value": column_name}, inplace=True)
        df["year"]       = pd.to_numeric(df["year"],       errors="coerce")
        df[column_name]  = pd.to_numeric(df[column_name],  errors="coerce")

        return df.dropna(subset=["year", column_name])

    except Exception as exc:
        logger.error("Error fetching %s: %s", indicator_code, exc, exc_info=True)
        return pd.DataFrame()


def fetch_data() -> pd.DataFrame:
    """
    Fetch GDP per capita from the World Bank API.
    Keeps the latest year per country and assigns an income group label.
    """
    logger.info("Fetching GDP per capita from World Bank API...")
    gdp_df = fetch_indicator("NY.GDP.PCAP.CD", "gdp_per_capita")

    if gdp_df.empty:
        logger.error("No data returned from API")
        return pd.DataFrame()

    logger.info("Filtering for the most recent year per country...")
    df = (
        gdp_df.sort_values("year")
        .groupby("iso3_code")        # group on iso3_code — stable across name changes
        .tail(1)
        .reset_index(drop=True)
    )

    # Assign income group — this is what was missing, causing NULL in the DB
    logger.info("Assigning income group labels...")
    df["income_group"] = df["gdp_per_capita"].apply(_assign_income_group)

    df["source"] = "World Bank"

    # Log a quick breakdown so you can verify in the console
    breakdown = df.groupby("income_group")["country"].count().to_dict()
    logger.info("Income group breakdown: %s", breakdown)

    return df


# ─────────────────────────────────────────────────────────────────────────────
# LOADING
# ─────────────────────────────────────────────────────────────────────────────

def _apply_schema(engine) -> bool:
    """
    Execute db/schema.sql as a single string (not split on ';').

    Splitting on ';' is unreliable for CREATE OR REPLACE VIEW statements.
    Passing the entire file lets PostgreSQL parse it correctly and creates
    the table, indexes, gdp_latest, and gdp_income_summary in one go.

    Returns True on success, False on failure.
    """
    schema_path = Path(__file__).resolve().parent.parent / "db" / "schema.sql"

    if not schema_path.exists():
        logger.error("CRITICAL: Schema file not found at %s", schema_path)
        return False

    with open(schema_path, "r") as fh:
        schema_sql = fh.read()

    with engine.begin() as conn:
        conn.execute(text(schema_sql))

    logger.info("Schema verified / created (gdp_data + gdp_latest + gdp_income_summary)")
    return True


def _upsert(df: pd.DataFrame, engine) -> None:
    """
    Insert rows into gdp_data; update on (country, year) conflict.

    Uses ON CONFLICT DO UPDATE so:
      - Existing rows are updated in place (no data loss)
      - The gdp_latest and gdp_income_summary views remain intact
      - Re-running the pipeline is fully idempotent
    """
    # Log arriving columns to make future mismatches easy to diagnose
    logger.info("DataFrame columns received: %s", df.columns.tolist())

    # Defensive: if income_group was not added by an upstream transform,
    # calculate it here so the pipeline never crashes on a missing column
    if "income_group" not in df.columns:
        logger.warning(
            "income_group missing from DataFrame — calculating in load.py. "
            "Add _assign_income_group() to your transform step to fix this properly."
        )
        df = df.copy()
        df["income_group"] = df["gdp_per_capita"].apply(_assign_income_group)

    if "source" not in df.columns:
        df = df.copy()
        df["source"] = "World Bank"

    upsert_sql = text(
        """
        INSERT INTO gdp_data (country, iso3_code, year, gdp_per_capita, income_group, source)
        VALUES (:country, :iso3_code, :year, :gdp_per_capita, :income_group, :source)
        ON CONFLICT (country, year)
        DO UPDATE SET
            iso3_code      = EXCLUDED.iso3_code,
            gdp_per_capita = EXCLUDED.gdp_per_capita,
            income_group   = EXCLUDED.income_group,
            source         = EXCLUDED.source,
            updated_at     = NOW();
        """
    )
    records = df[["country", "iso3_code", "year", "gdp_per_capita", "income_group", "source"]].to_dict(
        orient="records"
    )
    with engine.begin() as conn:
        conn.execute(upsert_sql, records)
    logger.info("Upserted %d records into gdp_data", len(records))


def load_data(df: pd.DataFrame) -> None:
    """Apply schema then upsert the DataFrame into gdp_data."""
    if df.empty:
        logger.warning("No data to load.")
        return

    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)

        if not _apply_schema(engine):
            return

        logger.info("Loading %d records into 'gdp_data'...", len(df))
        _upsert(df, engine)
        logger.info("Load complete.")

    except Exception as exc:
        logger.error("Error during database load: %s", exc, exc_info=True)
        raise
    finally:
        try:
            engine.dispose()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# ENTRYPOINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    data = fetch_data()

    if not data.empty:
        load_data(data)
        print("Success! Check your Postgres database.")
    else:
        print("Failed to fetch data from API.")