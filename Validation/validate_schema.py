"""Validation: Validate raw country JSON and produce validated parquet using AWS Glue."""

import sys
import logging
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Check if running as script or test
IS_TEST = 'pytest' in sys.modules or 'unittest' in sys.modules
IS_GLUE = not IS_TEST

def initialize_glue():
	"""Initialize Glue job only when running in Glue environment."""
	if not IS_GLUE:
		return None
	
	try:
		from awsglue.utils import getResolvedOptions
		from awsglue.context import GlueContext
		from awsglue.job import Job
		from pyspark.context import SparkContext
		
		args = getResolvedOptions(sys.argv, ['JOB_NAME', 'TempDir'])
		sc = SparkContext()
		glue_context = GlueContext(sc)
		spark = glue_context.spark_session
		job = Job(glue_context)
		job.init(args['JOB_NAME'], args)
		
		return {'job': job, 'spark': spark}
	except Exception as e:
		logger.error(f"Failed to initialize Glue: {str(e)}")
		return None

def run_validation(bucket_name, raw_zone, validated_zone, archive_zone, glue_context=None):
	"""Run validation job."""
	try:
		print("=" * 60)
		print("START: VALIDATION JOB")
		print("=" * 60)
		
		# Import Glue/Spark only when needed
		from pyspark.sql.functions import col
		import boto3
		
		if IS_GLUE and glue_context:
			spark = glue_context['spark']
			job = glue_context['job']
			print("✓ Using Glue environment")
		else:
			from pyspark.sql import SparkSession
			spark = SparkSession.builder.appName("ValidationJob").getOrCreate()
			job = None
			print("✓ Using local Spark environment")
		
		print(f"Configuration: Bucket={bucket_name}")
		
		# Step 1: Read raw data
		print("Step 1: Reading raw data from S3...")
		raw_path = f"s3://{bucket_name}/{raw_zone}/"
		try:
			raw_df = spark.read.json(raw_path)
			record_count_raw = raw_df.count()
			print(f"✓ Read {record_count_raw} raw records")
		except Exception as e:
			print(f"⚠️ No raw data found: {str(e)}")
			record_count_raw = 0
			return 0
		
		# Step 2: Validate data
		print("Step 2: Validating data (population > 0)...")
		validated_df = raw_df.filter(col("population").isNotNull() & (col("population") > 0))
		record_count_validated = validated_df.count()
		print(f"✓ Validated {record_count_validated} records")
		
		# Step 3: Write validated data
		print("Step 3: Writing validated data to S3...")
		validated_path = f"s3://{bucket_name}/{validated_zone}/"
		validated_df.write.mode("overwrite").parquet(validated_path)
		print(f"✓ Written to {validated_path}")
		
		# Step 4: Archive raw files
		print("Step 4: Archiving raw files...")
		s3_client = boto3.client("s3")
		response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=raw_zone)
		
		archived_count = 0
		if 'Contents' in response:
			for obj in response['Contents']:
				key = obj['Key']
				if not key.endswith('.keep'):
					archive_key = key.replace(raw_zone, archive_zone)
					s3_client.copy_object(
						CopySource={'Bucket': bucket_name, 'Key': key},
						Bucket=bucket_name,
						Key=archive_key
					)
					s3_client.delete_object(Bucket=bucket_name, Key=key)
					archived_count += 1
					print(f"✓ Archived: {key}")
		
		print(f"✓ Archived {archived_count} files")
		
		print("=" * 60)
		print("END: VALIDATION JOB - SUCCESS")
		print("=" * 60)
		
		if job:
			job.commit()
		
		return record_count_validated
	
	except Exception as e:
		print("=" * 60)
		print(f"ERROR: {str(e)}")
		print("=" * 60)
		import traceback
		traceback.print_exc()
		return 0

def main():
	"""Main entry point."""
	bucket_name = "data-pipeline-country-population"
	raw_zone = "raw/countries"
	validated_zone = "validated/countries"
	archive_zone = "raw/countries_archive"
	
	# Initialize Glue if running in Glue environment
	glue_context = initialize_glue() if IS_GLUE else None
	
	# Run validation
	record_count = run_validation(bucket_name, raw_zone, validated_zone, archive_zone, glue_context)
	logger.info(f"Validation completed: {record_count} records")

if __name__ == "__main__":
	if IS_GLUE:
		try:
			main()
		except Exception as e:
			logger.error(f"Fatal error: {str(e)}")
			sys.exit(1)
	else:
		main()