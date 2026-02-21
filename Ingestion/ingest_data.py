"""Ingestion: fetch country data from REST Countries API and upload to S3."""

import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("START: Ingestion Job")

def main():
	"""Main ingestion function."""
	try:
		logger.info("Importing libraries...")
		import requests
		import json
		import boto3
		
		logger.info("✓ Libraries imported")
		
		# Configuration
		api_url = "https://restcountries.com/v3.1/all"
		bucket_name = "data-pipeline-country-population"
		raw_zone = "raw/countries"
		
		logger.info(f"Configuration: API={api_url}, Bucket={bucket_name}, Zone={raw_zone}")
		
		# Step 1: Fetch from API
		logger.info("Step 1: Fetching from API...")
		try:
			response = requests.get(api_url, timeout=30)
			response.raise_for_status()
			data = response.json()
			logger.info(f"✓ API fetch successful - {len(data)} records")
		except Exception as e:
			logger.error(f"✗ API fetch failed: {str(e)}")
			raise
		
		# Step 2: Prepare data
		logger.info("Step 2: Preparing data...")
		timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		filename = f"countries_raw_{timestamp}.json"
		json_data = json.dumps(data, indent=2, default=str)
		logger.info(f"✓ Data prepared - filename: {filename}, size: {len(json_data)} bytes")
		
		# Step 3: Upload to S3
		logger.info("Step 3: Uploading to S3...")
		try:
			s3_client = boto3.client("s3")
			s3_key = f"{raw_zone}/{filename}"
			
			s3_client.put_object(
				Bucket=bucket_name,
				Key=s3_key,
				Body=json_data.encode('utf-8'),
				ContentType='application/json'
			)
			logger.info(f"✓ Upload successful - s3://{bucket_name}/{s3_key}")
		except Exception as e:
			logger.error(f"✗ S3 upload failed: {str(e)}")
			raise
		
		logger.info("END: Ingestion Job - SUCCESS")
		return True
	
	except Exception as e:
		logger.error(f"END: Ingestion Job - FAILED: {str(e)}")
		logger.exception("Full error trace:")
		raise

if __name__ == "__main__":
	try:
		success = main()
	except Exception as e:
		logger.error(f"Fatal error: {str(e)}")
