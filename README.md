# End-to-End GDP per Capita Data Pipeline

## Project Overview
This project implements an automated ETL (Extract, Transform, Load) pipeline that monitors global economic health by tracking GDP per capita. The system pulls data for 75+ economies from the World Bank API, classifies them into income groups using official Atlas thresholds, and loads the results into a PostgreSQL database.

The pipeline is designed to be idempotent, using SQL UPSERT logic to ensure that repeated runs update existing records without creating duplicates or breaking database views.

## Architecture
World Bank API → Python ETL (extract.py) → Transformation (transform.py) → PostgreSQL (load.py)
      ↑                ↓                           ↓                         ↓
Indicator:       Retry Logic                 Income Grouping            UPSERT Logic
NY.GDP.PCAP.CD   (urllib3/HTTPAdapter)       (Atlas Thresholds)         (ON CONFLICT)

## Power BI Dashboard
![GDP per Capita Dashboard](dashboard.png)

## Tools Used
* **Python 3.14**: Core programming language.
* **Requests & urllib3**: HTTP library with `HTTPAdapter` retry strategies for resilient API calls.
* **Pandas**: Data manipulation, cleaning, and income group classification.
* **SQLAlchemy**: Database ORM used for handling connections and executing UPSERT logic.
* **PostgreSQL**: Relational database for persistent storage.
* **Docker & Docker Compose**: Containerization and multi-container orchestration.
* **World Bank API**: Sourcing the `NY.GDP.PCAP.CD` (GDP per capita) indicator.

## Project Structure
```
gdp-per-capita-pipeline/
├── app/
│   ├── extract.py      # Data extraction from World Bank API with retry logic
│   ├── transform.py    # Data cleaning and Income Group classification
│   ├── load.py         # Data loading with PostgreSQL UPSERT logic
│   └── pipeline.py     # Main orchestration script
├── db/
│   └── schema.sql      # Database schema (tables, indexes, and views)
├── config/
│   └── config.py       # Configuration settings and DATABASE_URL
├── logs/               # Pipeline execution logs
├── requirements.txt    # Python dependencies
├── Dockerfile          # Docker image definition
├── docker-compose.yml  # Multi-container setup
└── README.md           # This file
```
## Setup Instructions
Prerequisites
Docker and Docker Compose

Python 3.14 (if running locally)

Running with Docker (Recommended)
Clone the repository:

Bash
git clone <repository-url>
cd gdp-per-capita-pipeline
Start the services:

Bash
docker-compose up --build
This initializes the PostgreSQL database, applies the schema, and runs the ETL pipeline automatically.

Running Locally
Install dependencies:

Bash
pip install -r requirements.txt
Run the pipeline:

Bash
python app/pipeline.py
Technical Features
Resilient Extraction: Implements a requests.Session with a Retry strategy to handle transient network errors (429, 500, 502, 503, 504).

Dynamic Classification: Automatically assigns economies to Low, Lower-middle, Upper-middle, or High income groups based on the latest World Bank Atlas thresholds.

Idempotent Loading: Uses ON CONFLICT (country, year) DO UPDATE to ensure that re-running the pipeline updates existing data instead of failing or duplicating.

Stable Mapping: Extracts the iso3_code directly from the API to ensure data remains consistent even if country names are updated.

## Logging
Pipeline logs are stored in logs/pipeline.log with timestamps and detailed execution info, including income group breakdowns for each run.

## API Source
Data is sourced from the World Bank World Development Indicators API:

Indicator: NY.GDP.PCAP.CD (GDP per capita, current USD).

Data Selection: Filters for the latest available year per country/economy.