# app/extract.py
import logging
import requests
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

RETRY_TOTAL = 3
RETRY_BACKOFF = 1


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

        # ── Capture iso3_code alongside country name ──────────────────────────
        # countryiso3code is always present in the API response.
        # Selecting it here ensures it flows through transform → load → DB.
        df = df[["country", "countryiso3code", "date", "value"]].copy()

        df["country"] = df["country"].apply(
            lambda x: x["value"] if isinstance(x, dict) else x
        )
        # Clean iso3_code: strip whitespace, replace empty strings with None
        df["countryiso3code"] = (
            df["countryiso3code"]
            .fillna("")
            .str.strip()
            .replace("", None)
        )

        df.rename(
            columns={
                "countryiso3code": "iso3_code",
                "date":            "year",
                "value":           column_name,
            },
            inplace=True,
        )

        df["year"]      = pd.to_numeric(df["year"],      errors="coerce")
        df[column_name] = pd.to_numeric(df[column_name], errors="coerce")

        return df.dropna(subset=["year", column_name])

    except Exception as exc:
        logging.error("Error fetching %s: %s", indicator_code, exc, exc_info=True)
        return pd.DataFrame()


def fetch_data() -> pd.DataFrame:
    """
    Fetch GDP per capita from the World Bank API.
    Keeps the latest year per country.
    iso3_code is extracted directly from the API response.
    """
    print("Fetching GDP per capita...")
    gdp_df = fetch_indicator("NY.GDP.PCAP.CD", "gdp_per_capita")

    if gdp_df.empty:
        logging.error("No data returned from API")
        return pd.DataFrame()

    print(f"GDP per capita: {len(gdp_df)} records")
    print("Selecting latest data per country...")

    df = (
        gdp_df.sort_values("year")
        .groupby("iso3_code")   # group on iso3_code — stable across country name changes
        .tail(1)
        .reset_index(drop=True)
    )

    df["source"] = "World Bank"
    print(f"Final dataset: {len(df)} countries")
    return df