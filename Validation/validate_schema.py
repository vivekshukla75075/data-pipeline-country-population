"""Validation: Validate raw country JSON and produce validated parquet using AWS Glue."""

import sys
import logging
import os
from datetime import datetime

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
	execution_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
	log_messages = []
	
	try:
		log_messages.append("=" * 60)
		log_messages.append("START: VALIDATION JOB")
		log_messages.append("=" * 60)
		log_messages.append("")
		
		print("=" * 60)
		print("START: VALIDATION JOB")
		print("=" * 60)
		
		# Import Glue/Spark only when needed
		from pyspark.sql.functions import col, from_json, schema_of_json
		from pyspark.sql.types import StructType, ArrayType
		import boto3
		
		if IS_GLUE and glue_context:
			spark = glue_context['spark']
			job = glue_context['job']
			log_messages.append("✓ Using Glue environment")
			print("✓ Using Glue environment")
		else:
			from pyspark.sql import SparkSession
			spark = SparkSession.builder.appName("ValidationJob").getOrCreate()
			job = None
			log_messages.append("✓ Using local Spark environment")
			print("✓ Using local Spark environment")
		
		log_messages.append(f"Configuration: Bucket={bucket_name}")
		log_messages.append(f"  Raw Zone: {raw_zone}")
		log_messages.append(f"  Validated Zone: {validated_zone}")
		log_messages.append(f"  Archive Zone: {archive_zone}")
		log_messages.append("")
		
		print(f"Configuration: Bucket={bucket_name}")
		print(f"  Raw Zone: {raw_zone}")
		print(f"  Validated Zone: {validated_zone}")
		print(f"  Archive Zone: {archive_zone}")
		
		# Step 1: Read raw data
		log_messages.append("Step 1: Reading raw data from S3...")
		print("Step 1: Reading raw data from S3...")
		raw_path = f"s3://{bucket_name}/{raw_zone}/"
		log_messages.append(f"  Reading from: {raw_path}")
		print(f"  Reading from: {raw_path}")
		
		try:
			# Try reading JSON with multiline option to handle pretty-printed JSON
			raw_df = spark.read.option("multiline", "true").json(raw_path)
			
			# Check if we got corrupted records
			if "_corrupt_record" in raw_df.columns:
				print("Warning: Found corrupted records, attempting to parse JSON array...")
				log_messages.append("Warning: Found corrupted records, attempting to parse JSON array...")
				
				# Read the entire file as text
				text_df = spark.read.text(raw_path)
				
				# Join all lines and parse as JSON
				import json
				json_content = ""
				for row in text_df.collect():
					json_content += row[0]
				
				# Parse JSON
				data = json.loads(json_content)
				
				# Convert to DataFrame
				raw_df = spark.createDataFrame(data)
				print(f"✓ Successfully parsed JSON array")
				log_messages.append(f"✓ Successfully parsed JSON array")
			
			record_count_raw = raw_df.count()
			log_messages.append(f"✓ Read {record_count_raw} raw records")
			print(f"✓ Read {record_count_raw} raw records")
			
			# Show schema
			print("Schema:")
			raw_df.printSchema()
			log_messages.append("Schema:")
			log_messages.append(raw_df.schema.json())
			
		except Exception as e:
			log_messages.append(f"⚠️ Error reading raw data: {str(e)}")
			print(f"⚠️ Error reading raw data: {str(e)}")
			logger.exception("Raw data read error:")
			
			# Write log before returning
			log_content = "\n".join(log_messages)
			s3_client = boto3.client("s3")
			s3_client.put_object(
				Bucket=bucket_name,
				Key=f"logs/validation_logs/validation_{execution_timestamp}.log",
				Body=log_content.encode('utf-8')
			)
			return 0
		
		log_messages.append("")
		
		# Step 2: Validate data
		log_messages.append("Step 2: Validating data (population > 0)...")
		print("Step 2: Validating data (population > 0)...")
		
		try:
			validated_df = raw_df.filter((col("population").isNotNull()) & (col("population") > 0))
			record_count_validated = validated_df.count()
			log_messages.append(f"✓ Validated {record_count_validated} records (filtered from {record_count_raw})")
			print(f"✓ Validated {record_count_validated} records (filtered from {record_count_raw})")
		except Exception as e:
			log_messages.append(f"Error filtering data: {str(e)}")
			print(f"Error filtering data: {str(e)}")
			raise
		
		log_messages.append("")
		
		# Step 3: Write validated data
		log_messages.append("Step 3: Writing validated data to S3...")
		print("Step 3: Writing validated data to S3...")
		validated_path = f"s3://{bucket_name}/{validated_zone}/"
		log_messages.append(f"  Writing to: {validated_path}")
		print(f"  Writing to: {validated_path}")
		
		try:
			validated_df.write \
				.mode("overwrite") \
				.format("parquet") \
				.option("compression", "snappy") \
				.save(validated_path)
			
			log_messages.append(f"✓ Written {record_count_validated} records to {validated_path}")
			print(f"✓ Written {record_count_validated} records to {validated_path}")
		except Exception as e:
			log_messages.append(f"⚠️ Error writing validated data: {str(e)}")
			print(f"⚠️ Error writing validated data: {str(e)}")
			logger.exception("Write error:")
			raise
		
		log_messages.append("")
		
		# Step 4: Archive raw files
		log_messages.append("Step 4: Archiving raw files...")
		print("Step 4: Archiving raw files...")
		s3_client = boto3.client("s3")
		
		try:
			response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=raw_zone)
			
			archived_count = 0
			if 'Contents' in response:
				for obj in response['Contents']:
					key = obj['Key']
					if not key.endswith('.keep') and key.endswith('.json'):
						archive_key = key.replace(raw_zone, archive_zone)
						
						s3_client.copy_object(
							CopySource={'Bucket': bucket_name, 'Key': key},
							Bucket=bucket_name,
							Key=archive_key
						)
						log_messages.append(f"  Copied to archive: {archive_key}")
						print(f"  Copied to archive: {archive_key}")
						
						s3_client.delete_object(Bucket=bucket_name, Key=key)
						log_messages.append(f"  ✓ Archived: {key}")
						print(f"  ✓ Archived: {key}")
						archived_count += 1
			
			log_messages.append(f"✓ Archived {archived_count} files")
			print(f"✓ Archived {archived_count} files")
		except Exception as e:
			log_messages.append(f"⚠️ Error archiving files: {str(e)}")
			print(f"⚠️ Error archiving files: {str(e)}")
			logger.exception("Archive error:")
		
		log_messages.append("")
		log_messages.append("=" * 60)
		log_messages.append("END: VALIDATION JOB - SUCCESS")
		log_messages.append("=" * 60)
		log_messages.append(f"Summary:")
		log_messages.append(f"  Raw records read: {record_count_raw}")
		log_messages.append(f"  Validated records: {record_count_validated}")
		log_messages.append(f"  Archived files: {archived_count}")
		
		print("=" * 60)
		print("END: VALIDATION JOB - SUCCESS")
		print("=" * 60)
		print(f"Summary:")
		print(f"  Raw records read: {record_count_raw}")
		print(f"  Validated records: {record_count_validated}")
		print(f"  Archived files: {archived_count}")
		
		if job:
			job.commit()
			log_messages.append("✓ Glue job committed")
			print("✓ Glue job committed")
		
		# Write log to S3
		log_content = "\n".join(log_messages)
		s3_client.put_object(
			Bucket=bucket_name,
			Key=f"logs/validation_logs/validation_{execution_timestamp}.log",
			Body=log_content.encode('utf-8')
		)
		
		return record_count_validated
	
	except Exception as e:
		log_messages.append("")
		log_messages.append("=" * 60)
		log_messages.append(f"ERROR: {str(e)}")
		log_messages.append("=" * 60)
		import traceback
		log_messages.append(traceback.format_exc())
		logger.exception("Validation job failed:")
		
		print("=" * 60)
		print(f"ERROR: {str(e)}")
		print("=" * 60)
		traceback.print_exc()
		
		# Write error log
		log_content = "\n".join(log_messages)
		s3_client = boto3.client("s3")
		s3_client.put_object(
			Bucket=bucket_name,
			Key=f"logs/validation_logs/validation_error_{execution_timestamp}.log",
			Body=log_content.encode('utf-8')
		)
		
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