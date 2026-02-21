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

def fetch_from_api(url="https://restcountries.com/v3.1/all", timeout=30, retries=3, retry_delay=5):
	"""Fetch country data from API with retry logic."""
	import time
	
	for attempt in range(retries):
		try:
			logger.info(f"Fetching data from API (attempt {attempt + 1}/{retries}): {url}")
			response = requests.get(url, timeout=timeout)
			response.raise_for_status()
			logger.info("✓ Successfully fetched data from API")
			return response.json()
		except requests.exceptions.RequestException as e:
			if attempt < retries - 1:
				logger.warning(f"API fetch failed, retrying in {retry_delay}s: {str(e)}")
				time.sleep(retry_delay)
			else:
				logger.exception(f"Failed to fetch data from API after {retries} attempts: {str(e)}")
				raise

def save_to_local(data, file_path):
	"""Save data to local JSON file."""
	try:
		os.makedirs(os.path.dirname(file_path), exist_ok=True)
		with open(file_path, "w", encoding="utf-8") as f:
			json.dump(data, f, indent=2)
		logger.info(f"✓ Saved data to local file: {file_path}")
		return file_path
	except Exception as e:
		logger.exception(f"Failed to save data locally: {str(e)}")
		raise

def upload_to_s3(local_path, bucket_name, s3_key):
	"""Upload file to S3 with error handling."""
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
	"""Generate filename with date and time."""
	timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
	return f"countries_raw_{timestamp}.json"

def main_ingestion(bucket_name):
	"""Main ingestion logic."""
	try:
		api_url = os.environ.get("API_URL", "https://restcountries.com/v3.1/all")
		api_timeout = int(os.environ.get("API_TIMEOUT", 30))
		api_retries = int(os.environ.get("API_RETRIES", 3))
		raw_zone = os.environ.get("RAW_ZONE", "raw/countries")
		
		logger.info(f"Starting ingestion job for {api_url}")
		
		# Fetch data from API
		data = fetch_from_api(api_url, api_timeout, api_retries)
		logger.info(f"Fetched {len(data)} records from API")
		
		# Generate filename with timestamp
		filename = generate_filename_with_timestamp()
		local_path = f"/tmp/{filename}"
		
		# Save locally
		save_to_local(data, local_path)
		
		# Upload to S3
		s3_key = f"{raw_zone}/{filename}"
		upload_to_s3(local_path, bucket_name, s3_key)
		
		logger.info(f"✓ Ingestion completed successfully")
		logger.info(f"File: {filename}")
		logger.info(f"Location: s3://{bucket_name}/{s3_key}")
		return True
	except Exception as e:
		logger.exception("Ingestion job failed")
		return False

def main():
	"""Main entry point."""
	try:
		# Check if running in Glue
		is_glue = False
		try:
			from awsglue.utils import getResolvedOptions
			from awsglue.context import GlueContext
			from awsglue.job import Job
			from pyspark.context import SparkContext
			
			# Initialize Glue job
			args = getResolvedOptions(sys.argv, ['JOB_NAME'])
			sc = SparkContext()
			glue_context = GlueContext(sc)
			job = Job(glue_context)
			job.init(args['JOB_NAME'], args)
			is_glue = True
			
			logger.info(f"Running as Glue job: {args['JOB_NAME']}")
		except:
			logger.info("Not running in Glue environment, running locally")
		
		bucket_name = os.environ.get("S3_BUCKET", "data-pipeline-country-population")
		success = main_ingestion(bucket_name)
		
		# Commit Glue job if running
		if is_glue:
			try:
				job.commit()
				logger.info("✓ Glue job committed successfully")
			except Exception as e:
				logger.warning(f"Could not commit Glue job: {str(e)}")
		
		return success
	except Exception as e:
		logger.exception("Ingestion failed")
		return False

if __name__ == "__main__":
	success = main()
	# Don't exit with error code in Glue - let Glue handle it
	if not success:
		logger.error("Ingestion script completed with errors")
