"""Ingestion: fetch country data from REST Countries API and upload to S3."""

import sys
import os

# Add logging setup at the very top
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
	import requests
	import json
	from datetime import datetime
	import boto3
	
	def main():
		"""Main ingestion function."""
		logger.info("=== Starting Ingestion Job ===")
		
		try:
			# Configuration
			api_url = "https://restcountries.com/v3.1/all"
			bucket_name = os.environ.get("S3_BUCKET", "data-pipeline-country-population")
			raw_zone = "raw/countries"
			
			logger.info(f"API URL: {api_url}")
			logger.info(f"S3 Bucket: {bucket_name}")
			
			# Fetch from API
			logger.info("Fetching data from API...")
			response = requests.get(api_url, timeout=30)
			response.raise_for_status()
			data = response.json()
			logger.info(f"✓ Fetched {len(data)} records from API")
			
			# Generate filename with timestamp
			timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
			filename = f"countries_raw_{timestamp}.json"
			logger.info(f"Generated filename: {filename}")
			
			# Save to local temp
			local_path = f"/tmp/{filename}"
			logger.info(f"Saving to local: {local_path}")
			with open(local_path, "w") as f:
				json.dump(data, f, indent=2)
			logger.info(f"✓ Saved locally")
			
			# Upload to S3
			s3_key = f"{raw_zone}/{filename}"
			logger.info(f"Uploading to S3: s3://{bucket_name}/{s3_key}")
			s3_client = boto3.client("s3")
			s3_client.upload_file(local_path, bucket_name, s3_key)
			logger.info(f"✓ Uploaded successfully")
			
			logger.info("=== Ingestion Job Completed Successfully ===")
			return True
			
		except Exception as e:
			logger.exception(f"ERROR in ingestion: {str(e)}")
			return False
	
	# Run main
	success = main()
	
except Exception as e:
	logger.exception(f"FATAL ERROR: {str(e)}")
	sys.exit(1)
