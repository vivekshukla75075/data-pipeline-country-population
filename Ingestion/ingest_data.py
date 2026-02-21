"""Ingestion: fetch country data from REST Countries API using AWS Glue PySpark."""

import sys
import logging
from datetime import datetime

# Setup logging FIRST
logging.basicConfig(
	level=logging.INFO, 
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info("=== Starting Ingestion Script ===")

try:
	# Import Glue libraries
	from awsglue.utils import getResolvedOptions
	from awsglue.context import GlueContext
	from awsglue.job import Job
	from pyspark.context import SparkContext
	
	logger.info("✓ Glue imports successful")
	IS_GLUE = True
	
except ImportError as e:
	logger.error(f"Glue imports failed: {str(e)}")
	IS_GLUE = False

def fetch_api_data(url="https://restcountries.com/v3.1/all"):
	"""Fetch data from REST Countries API."""
	try:
		import requests
		logger.info(f"Fetching data from API: {url}")
		response = requests.get(url, timeout=30)
		response.raise_for_status()
		data = response.json()
		logger.info(f"✓ Fetched {len(data)} records from API")
		return data
	except Exception as e:
		logger.exception(f"Failed to fetch from API: {str(e)}")
		raise

def save_to_s3(data, bucket_name, s3_path):
	"""Save fetched data as JSON to S3."""
	try:
		import json
		import boto3
		
		logger.info(f"Saving data to S3...")
		
		# Generate filename with timestamp
		timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		filename = f"countries_raw_{timestamp}.json"
		s3_key = f"{s3_path}/{filename}"
		
		# Convert data to JSON
		json_data = json.dumps(data, indent=2, default=str)
		
		# Upload to S3
		s3_client = boto3.client("s3")
		s3_client.put_object(
			Bucket=bucket_name,
			Key=s3_key,
			Body=json_data.encode('utf-8'),
			ContentType='application/json'
		)
		
		logger.info(f"✓ Saved JSON file: s3://{bucket_name}/{s3_key}")
		return True
	except Exception as e:
		logger.exception(f"Failed to save to S3: {str(e)}")
		raise

def main_glue():
	"""Main Glue job function."""
	try:
		logger.info("Running in Glue environment")
		
		# Initialize Glue job
		args = getResolvedOptions(sys.argv, ['JOB_NAME', 'TempDir'])
		logger.info(f"Job Name: {args['JOB_NAME']}")
		
		sc = SparkContext()
		glue_context = GlueContext(sc)
		job = Job(glue_context)
		job.init(args['JOB_NAME'], args)
		
		logger.info("✓ Glue context initialized")
		
		# Configuration
		api_url = "https://restcountries.com/v3.1/all"
		bucket_name = "data-pipeline-country-population"
		raw_zone = "raw/countries"
		
		logger.info(f"API URL: {api_url}")
		logger.info(f"S3 Bucket: {bucket_name}")
		logger.info(f"Raw Zone: {raw_zone}")
		
		# Fetch from API
		data = fetch_api_data(api_url)
		
		# Save to S3
		save_to_s3(data, bucket_name, raw_zone)
		
		logger.info("=== Ingestion Job Completed Successfully ===")
		
		# Commit Glue job
		job.commit()
		logger.info("✓ Glue job committed")
		
	except Exception as e:
		logger.exception(f"Glue job failed: {str(e)}")
		raise

def main_local():
	"""Main function for local testing."""
	try:
		logger.info("Running locally (not in Glue)")
		
		# Configuration
		api_url = "https://restcountries.com/v3.1/all"
		bucket_name = "data-pipeline-country-population"
		raw_zone = "raw/countries"
		
		logger.info(f"API URL: {api_url}")
		logger.info(f"S3 Bucket: {bucket_name}")
		logger.info(f"Raw Zone: {raw_zone}")
		
		# Fetch from API
		data = fetch_api_data(api_url)
		
		# Save to S3
		save_to_s3(data, bucket_name, raw_zone)
		
		logger.info("=== Ingestion Completed Successfully ===")
		
	except Exception as e:
		logger.exception(f"Ingestion failed: {str(e)}")
		raise

if __name__ == "__main__":
	try:
		if IS_GLUE:
			main_glue()
		else:
			main_local()
	except Exception as e:
		logger.exception(f"Fatal error: {str(e)}")
		# Don't exit with error code - let CloudWatch Logs capture it
