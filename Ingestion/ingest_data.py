"""Ingestion: fetch country data from REST Countries API using AWS Glue PySpark."""

import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
	# Import Glue libraries
	from awsglue.utils import getResolvedOptions
	from awsglue.context import GlueContext
	from awsglue.job import Job
	from pyspark.context import SparkContext
	from pyspark.sql.types import StructType, StructField, StringType, LongType, ArrayType, DoubleType
	from pyspark.sql.functions import current_timestamp
	
	IS_GLUE = True
except ImportError:
	IS_GLUE = False
	logger.error("Glue imports failed - not running in Glue environment")
	sys.exit(1)

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

def save_to_s3(spark, data, bucket_name, s3_path):
	"""Save fetched data as JSON to S3."""
	try:
		import json
		from io import StringIO
		
		logger.info(f"Converting data to JSON and uploading to S3...")
		
		# Convert to JSON string
		json_data = json.dumps(data, indent=2, default=str)
		
		# Create RDD and convert to DataFrame (for Spark)
		rdd = spark.sparkContext.parallelize([json_data])
		
		# Write to S3
		s3_path_full = f"s3://{bucket_name}/{s3_path}"
		logger.info(f"Writing to: {s3_path_full}")
		
		rdd.saveAsTextFile(s3_path_full)
		
		logger.info(f"✓ Data saved to S3: {s3_path_full}")
		return True
	except Exception as e:
		logger.exception(f"Failed to save to S3: {str(e)}")
		raise

def save_as_json_file(spark, data, bucket_name, s3_path):
	"""Save data as single JSON file to S3 (better approach)."""
	try:
		import json
		import boto3
		from datetime import datetime
		
		logger.info(f"Saving data as JSON file to S3...")
		
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
		logger.exception(f"Failed to save JSON file: {str(e)}")
		raise

def main():
	"""Main Glue job function."""
	try:
		logger.info("=== Starting Ingestion Job ===")
		
		# Initialize Glue job
		args = getResolvedOptions(sys.argv, ['JOB_NAME', 'TempDir'])
		sc = SparkContext()
		glue_context = GlueContext(sc)
		spark = glue_context.spark_session
		job = Job(glue_context)
		job.init(args['JOB_NAME'], args)
		
		logger.info(f"Job Name: {args['JOB_NAME']}")
		
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
		save_as_json_file(spark, data, bucket_name, raw_zone)
		
		logger.info("=== Ingestion Job Completed Successfully ===")
		
		# Commit Glue job
		job.commit()
		return True
		
	except Exception as e:
		logger.exception("Ingestion job failed")
		return False

if __name__ == "__main__":
	if IS_GLUE:
		success = main()
		sys.exit(0 if success else 1)
	else:
		logger.error("Must run in AWS Glue environment")
		sys.exit(1)
