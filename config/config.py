import os

# Database configuration
# Force Postgres for local use
DB_TYPE = os.getenv('DB_TYPE', 'postgres') 

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'gdp_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'This1sS8e')

# Correct format for SQLAlchemy 2.0+ is postgresql://
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
