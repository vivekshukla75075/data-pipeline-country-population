"""Ingestion: fetch country data from REST Countries API and upload to S3.

Description:
- Fetches data from https://restcountries.com/v3.1/all
- Saves with timestamp filename
- Uploads to S3 raw zone
- Full error handling and logging
"""

import requests
import json
import os
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_from_api(url="https://restcountries.com/v3.1/all", timeout=30, retries=3):
	"""Fetch country data from API with retry logic."""
	import time
	
	for attempt in range(retries):
		try:
			logger.info(f"Fetching from API (attempt {attempt + 1}/{retries}): {url}")
			response = requests.get(url, timeout=timeout)
			response.raise_for_status()
			logger.info(f"✓ Successfully fetched {len(response.json())} records from API")
			return response.json()
		except Exception as e:
			if attempt < retries - 1:
				logger.warning(f"Fetch failed, retrying: {str(e)}")
				time.sleep(5)
			else:
				logger.exception(f"Failed after {retries} attempts")
				raise

def save_to_local(data, file_path):
	"""Save data to local file."""
	try:
		os.makedirs(os.path.dirname(file_path), exist_ok=True)
		with open(file_path, "w", encoding="utf-8") as f:
			json.dump(data, f, indent=2)
		logger.info(f"✓ Saved to local file: {file_path}")
		return file_path
	except Exception as e:
		logger.exception(f"Failed to save locally: {str(e)}")
		raise

def upload_to_s3(local_path, bucket_name, s3_key):
	"""Upload file to S3."""
	try:
		import boto3
		s3_client = boto3.client("s3")
		s3_client.upload_file(local_path, bucket_name, s3_key)
		logger.info(f"✓ Uploaded to S3: s3://{bucket_name}/{s3_key}")
		return True
	except Exception as e:
		logger.exception(f"Failed to upload to S3: {str(e)}")
		raise

def generate_filename_with_timestamp():
	"""Generate filename with timestamp."""
	timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
	return f"countries_raw_{timestamp}.json"

def main():
	"""Main ingestion logic."""
	try:
		# Get configuration from environment
		api_url = os.environ.get("API_URL", "https://restcountries.com/v3.1/all")
		bucket_name = os.environ.get("S3_BUCKET", "data-pipeline-country-population")
		raw_zone = os.environ.get("RAW_ZONE", "raw/countries")
		
		logger.info(f"Starting ingestion job")
		logger.info(f"API URL: {api_url}")
		logger.info(f"S3 Bucket: {bucket_name}")
		logger.info(f"Raw Zone: {raw_zone}")
		
		# Fetch from API
		data = fetch_from_api(api_url)
		
		# Generate filename with timestamp
		filename = generate_filename_with_timestamp()
		local_path = f"/tmp/{filename}"
		
		# Save locally
		save_to_local(data, local_path)
		
		# Upload to S3
		s3_key = f"{raw_zone}/{filename}"
		upload_to_s3(local_path, bucket_name, s3_key)
		
		logger.info(f"✓ Ingestion completed successfully")
		logger.info(f"Output: s3://{bucket_name}/{s3_key}")
		
		return True
	
	except Exception as e:
		logger.exception("Ingestion job failed")
		return False

if __name__ == "__main__":
	try:
		# Check if running in Glue
		try:
			from awsglue.utils import getResolvedOptions
			from awsglue.context import GlueContext
			from awsglue.job import Job
			from pyspark.context import SparkContext
			
			args = getResolvedOptions(sys.argv, ['JOB_NAME'])
			sc = SparkContext()
			glue_context = GlueContext(sc)
			job = Job(glue_context)
			job.init(args['JOB_NAME'], args)
			
			logger.info(f"Running as Glue job: {args['JOB_NAME']}")
			success = main()
			job.commit()
		except:
			# Not running in Glue
			logger.info("Running as local script")
			success = main()
		
		if not success:
			logger.error("Job completed with errors")
	except Exception as e:
		logger.exception("Fatal error")
