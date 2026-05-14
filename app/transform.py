# transform.py
import pandas as pd
import logging

# ── World Bank Atlas income thresholds (FY2024, GNI per capita USD) ───────────
# https://datahelpdesk.worldbank.org/knowledgebase/articles/906519
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


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforms raw GDP per capita data into a cleaned DataFrame.

    Parameters:
        df (pandas.DataFrame): Input DataFrame from extract.

    Returns:
        pandas.DataFrame: Cleaned DataFrame with numeric types, no duplicates,
                          and an income_group column populated from World Bank
                          Atlas thresholds.
    """
    if df.empty:
        return df

    # ── Column selection ──────────────────────────────────────────────────────
    # income_group is calculated here — it must be in this list so load.py
    # receives it and does not crash with KeyError
    expected_cols = ['country', 'iso3_code', 'year', 'gdp_per_capita', 'income_group', 'source']

    for col in expected_cols:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[expected_cols].copy()

    # ── Drop rows with no GDP value ───────────────────────────────────────────
    df = df.dropna(subset=['gdp_per_capita'])

    # ── Cast types ────────────────────────────────────────────────────────────
    df['year'] = pd.to_numeric(df['year'], errors='coerce').astype('Int64')
    df['gdp_per_capita'] = pd.to_numeric(df['gdp_per_capita'], errors='coerce')

    # ── Assign income group ───────────────────────────────────────────────────
    # Always recalculate from gdp_per_capita so the column is never NULL,
    # even if the upstream extract did not provide it
    df['income_group'] = df['gdp_per_capita'].apply(_assign_income_group)

    # ── Remove duplicates ─────────────────────────────────────────────────────
    df = df.drop_duplicates()

    # Log a breakdown for quick sanity-checking in the console
    breakdown = df.groupby('income_group')['country'].count().to_dict()
    logging.info("Transform complete: %d rows | income groups: %s", len(df), breakdown)

    return df


if __name__ == "__main__":
    sample_data = pd.DataFrame([
        {'country': 'Norway',     'year': 2023, 'gdp_per_capita': 101890, 'source': 'World Bank'},
        {'country': 'India',      'year': 2023, 'gdp_per_capita': 2540,   'source': 'World Bank'},
        {'country': 'Bangladesh', 'year': 2023, 'gdp_per_capita': 2688,   'source': 'World Bank'},
        {'country': 'Burundi',    'year': 2023, 'gdp_per_capita': 217,    'source': 'World Bank'},
    ])
    result = transform_data(sample_data)
    print(result.to_string(index=False))