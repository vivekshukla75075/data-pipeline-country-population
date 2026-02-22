"""Validation: Validate raw country JSON and produce validated parquet using AWS Glue."""

import sys
import logging
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("=" * 60)
print("START: VALIDATION JOB")
print("=" * 60)

try:
	from awsglue.utils import getResolvedOptions
	from awsglue.context import GlueContext
	from awsglue.job import Job
	from pyspark.context import SparkContext
	from pyspark.sql.functions import col
	import boto3
	
	print("✓ Glue imports successful")
	
	# Initialize Glue
	args = getResolvedOptions(sys.argv, ['JOB_NAME', 'TempDir'])
	sc = SparkContext()
	glue_context = GlueContext(sc)
	spark = glue_context.spark_session
	job = Job(glue_context)
	job.init(args['JOB_NAME'], args)
	
	print(f"✓ Glue job initialized: {args['JOB_NAME']}")
	
	# Configuration
	bucket_name = "data-pipeline-country-population"
	raw_zone = "raw/countries"
	validated_zone = "validated/countries"
	archive_zone = "raw/countries_archive"
	
	print(f"Configuration: Bucket={bucket_name}")
	
	# Step 1: Read raw data
	print("Step 1: Reading raw data from S3...")
	raw_path = f"s3://{bucket_name}/{raw_zone}/"
	raw_df = spark.read.json(raw_path)
	record_count_raw = raw_df.count()
	print(f"✓ Read {record_count_raw} raw records")
	
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
	
	if 'Contents' in response:
		archived_count = 0
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
	
	job.commit()

except Exception as e:
	print("=" * 60)
	print(f"ERROR: {str(e)}")
	print("=" * 60)
	import traceback
	traceback.print_exc()
	sys.exit(1)