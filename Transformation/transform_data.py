"""Transformation: Transform and partition country data using AWS Glue."""

import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

execution_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_messages = []

print("=" * 60)
print("START: TRANSFORMATION JOB")
print("=" * 60)

log_messages.append("=" * 60)
log_messages.append("START: TRANSFORMATION JOB")
log_messages.append("=" * 60)
log_messages.append("")

def check_s3_data(bucket_name, path_prefix):
	"""Check if data exists in S3 path."""
	import boto3
	s3_client = boto3.client("s3")
	
	try:
		response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=path_prefix)
		
		if 'Contents' in response:
			file_count = len(response['Contents'])
			print(f"  Found {file_count} files in s3://{bucket_name}/{path_prefix}")
			for obj in response['Contents']:
				print(f"    - {obj['Key']}")
			return True
		else:
			print(f"  No files found in s3://{bucket_name}/{path_prefix}")
			return False
	except Exception as e:
		print(f"  Error checking path: {str(e)}")
		return False

try:
	from awsglue.utils import getResolvedOptions
	from awsglue.context import GlueContext
	from awsglue.job import Job
	from pyspark.context import SparkContext
	from pyspark.sql.functions import col, coalesce
	import boto3
	
	print("✓ Glue imports successful")
	log_messages.append("✓ Glue imports successful")
	
	# Initialize Glue
	args = getResolvedOptions(sys.argv, ['JOB_NAME', 'TempDir'])
	sc = SparkContext()
	glue_context = GlueContext(sc)
	spark = glue_context.spark_session
	job = Job(glue_context)
	job.init(args['JOB_NAME'], args)
	
	print(f"✓ Glue job initialized: {args['JOB_NAME']}")
	log_messages.append(f"✓ Glue job initialized: {args['JOB_NAME']}")
	log_messages.append("")
	
	# Configuration
	bucket_name = "data-pipeline-country-population"
	validated_zone = "validated/countries"
	curated_zone = "curated/countries"
	
	print(f"Configuration: Bucket={bucket_name}")
	log_messages.append(f"Configuration: Bucket={bucket_name}")
	print(f"  Validated Zone: {validated_zone}")
	log_messages.append(f"  Validated Zone: {validated_zone}")
	print(f"  Curated Zone: {curated_zone}")
	log_messages.append(f"  Curated Zone: {curated_zone}")
	log_messages.append("")
	
	# Step 1: Check validated data exists
	print("Step 1: Checking validated data in S3...")
	log_messages.append("Step 1: Checking validated data in S3...")
	validated_path = f"s3://{bucket_name}/{validated_zone}/"
	print(f"  Checking: {validated_path}")
	log_messages.append(f"  Checking: {validated_path}")
	
	s3_client = boto3.client("s3")
	response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=validated_zone)
	
	if 'Contents' not in response:
		error_msg = "No validated data found!"
		print(error_msg)
		log_messages.append(error_msg)
		raise Exception(error_msg)
	
	print(f"✓ Found validated data files")
	log_messages.append(f"✓ Found validated data files")
	log_messages.append("")
	
	# Step 2: Read validated data
	print("Step 2: Reading validated data from S3...")
	log_messages.append("Step 2: Reading validated data from S3...")
	print(f"  Reading from: {validated_path}")
	log_messages.append(f"  Reading from: {validated_path}")
	
	try:
		validated_df = spark.read.parquet(validated_path)
		record_count = validated_df.count()
		print(f"✓ Read {record_count} validated records (Parquet format)")
		log_messages.append(f"✓ Read {record_count} validated records (Parquet format)")
	except Exception as e1:
		print(f"  Parquet read failed: {str(e1)}")
		print("  Trying JSON format...")
		log_messages.append(f"  Parquet read failed: {str(e1)}")
		log_messages.append("  Trying JSON format...")
		
		try:
			validated_df = spark.read.json(validated_path)
			record_count = validated_df.count()
			print(f"✓ Read {record_count} validated records (JSON format)")
			log_messages.append(f"✓ Read {record_count} validated records (JSON format)")
		except Exception as e2:
			error_msg = f"Could not read validated data: Parquet({e1}), JSON({e2})"
			print(error_msg)
			log_messages.append(error_msg)
			logger.exception("Data read errors:")
			raise Exception(error_msg)
	
	log_messages.append("")
	
	# Step 3: Transform data
	print("Step 3: Transforming data...")
	log_messages.append("Step 3: Transforming data...")
	print(f"  Flattening nested columns...")
	log_messages.append(f"  Flattening nested columns...")
	
	try:
		transformed_df = validated_df.select(
			col("name.common").alias("country_name"),
			col("region"),
			col("subregion"),
			col("population"),
			col("area"),
			coalesce(col("capital")[0], col("capital")).alias("capital_city"),
			coalesce(col("currencies"), col("name.common")).alias("currency")
		)
		print(f"✓ Transformed {record_count} records")
		log_messages.append(f"✓ Transformed {record_count} records")
		print(f"  Schema: country_name, region, subregion, population, area, capital_city, currency")
		log_messages.append(f"  Schema: country_name, region, subregion, population, area, capital_city, currency")
	except Exception as e:
		error_msg = f"Error transforming data: {str(e)}"
		print(error_msg)
		log_messages.append(error_msg)
		logger.exception("Transform error:")
		raise
	
	log_messages.append("")
	
	# Step 4: Write curated data (partitioned by region)
	print("Step 4: Writing curated data to S3 (partitioned by region)...")
	log_messages.append("Step 4: Writing curated data to S3 (partitioned by region)...")
	curated_path = f"s3://{bucket_name}/{curated_zone}/"
	print(f"  Writing to: {curated_path}")
	log_messages.append(f"  Writing to: {curated_path}")
	print(f"  Partitioning by: region")
	log_messages.append(f"  Partitioning by: region")
	
	try:
		transformed_df.write \
			.mode("overwrite") \
			.format("parquet") \
			.option("compression", "snappy") \
			.partitionBy("region") \
			.save(curated_path)
		
		print(f"✓ Written {record_count} records to {curated_path}")
		log_messages.append(f"✓ Written {record_count} records to {curated_path}")
		print(f"✓ Data partitioned by region")
		log_messages.append(f"✓ Data partitioned by region")
	except Exception as e:
		error_msg = f"Error writing curated data: {str(e)}"
		print(error_msg)
		log_messages.append(error_msg)
		logger.exception("Write error:")
		raise
	
	log_messages.append("")
	log_messages.append("=" * 60)
	log_messages.append("END: TRANSFORMATION JOB - SUCCESS")
	log_messages.append("=" * 60)
	log_messages.append(f"Summary:")
	log_messages.append(f"  Records transformed: {record_count}")
	log_messages.append(f"  Output location: s3://{bucket_name}/{curated_zone}/")
	log_messages.append(f"  Partitioned by: region")
	
	print("=" * 60)
	print("END: TRANSFORMATION JOB - SUCCESS")
	print("=" * 60)
	print(f"Summary:")
	print(f"  Records transformed: {record_count}")
	print(f"  Output location: s3://{bucket_name}/{curated_zone}/")
	print(f"  Partitioned by: region")
	
	job.commit()
	log_messages.append("✓ Glue job committed")
	print("✓ Glue job committed")
	
	# Write log to S3
	log_content = "\n".join(log_messages)
	s3_client = boto3.client("s3")
	s3_client.put_object(
		Bucket=bucket_name,
		Key=f"logs/transformation_logs/transformation_{execution_timestamp}.log",
		Body=log_content.encode('utf-8')
	)

except Exception as e:
	log_messages.append("")
	log_messages.append("=" * 60)
	log_messages.append(f"ERROR: {str(e)}")
	log_messages.append("=" * 60)
	import traceback
	log_messages.append(traceback.format_exc())
	logger.exception("Transformation job failed:")
	
	print("=" * 60)
	print(f"ERROR: {str(e)}")
	print("=" * 60)
	import traceback
	traceback.print_exc()
	
	# Write error log
	log_content = "\n".join(log_messages)
	s3_client = boto3.client("s3")
	s3_client.put_object(
		Bucket=bucket_name,
		Key=f"logs/transformation_logs/transformation_error_{execution_timestamp}.log",
		Body=log_content.encode('utf-8')
	)
	
	sys.exit(1)