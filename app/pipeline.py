import logging
from app.extract import fetch_data
from app.transform import transform_data
from app.load import load_data

# Set up logging
logging.basicConfig(
    filename='logs/pipeline.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def run_pipeline():
    """
    Runs the complete ETL pipeline: Extract, Transform, Load GDP per capita data.
    """
    logging.info("Pipeline started")
    
    try:
        # Extract
        logging.info("Starting data extraction")
        raw_df = fetch_data()
        logging.info(f"Extracted {len(raw_df)} raw records")
        
        # Transform
        logging.info("Starting data transformation")
        cleaned_df = transform_data(raw_df)
        logging.info(f"Transformed to {len(cleaned_df)} cleaned records")
        
        # Load
        logging.info("Starting data loading")
        load_data(cleaned_df)
        logging.info("Data loading completed")
        
        logging.info("Pipeline completed successfully")
        
    except Exception as e:
        logging.error(f"Pipeline failed: {e}")
        raise

if __name__ == "__main__":
    run_pipeline()