"""Transformation: Transform and partition country data using AWS Glue."""

import sys
import logging
from datetime import datetime

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

try:
	from awsglue.utils import getResolvedOptions
	from awsglue.context import GlueContext
	from awsglue.job import Job
	from pyspark.context import SparkContext
	from pyspark.sql.functions import col, coalesce
	import boto3
	import json
	
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
	
	# Step 1: Check validated data
	print("Step 1: Checking validated data in S3...")
	log_messages.append("Step 1: Checking validated data in S3...")
	validated_path = f"s3://{bucket_name}/{validated_zone}/"
	print(f"  Checking: {validated_path}")
	log_messages.append(f"  Checking: {validated_path}")
	
	s3_client = boto3.client("s3")
	response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=validated_zone)
	
	parquet_files = []
	if 'Contents' in response:
		parquet_files = [obj for obj in response['Contents'] if obj['Key'].endswith('.parquet')]
	
	if not parquet_files:
		error_msg = "No validated data found!"
		print(error_msg)
		log_messages.append(error_msg)
		log_messages.append("")
		log_messages.append("Available files in validated zone:")
		if 'Contents' in response:
			for obj in response['Contents']:
				log_messages.append(f"  - {obj['Key']}")
				print(f"  - {obj['Key']}")
		else:
			log_messages.append("  (no files found)")
			print("  (no files found)")
		
		log_messages.append("")
		log_messages.append("Checking for JSON files in validated zone...")
		print("Checking for JSON files in validated zone...")
		json_files = [obj for obj in response.get('Contents', []) if obj['Key'].endswith('.json')]
		if json_files:
			log_messages.append("Found JSON files, attempting to read...")
			print("Found JSON files, attempting to read...")
			for f in json_files:
				log_messages.append(f"  - {f['Key']}")
				print(f"  - {f['Key']}")
		
		log_messages.append("")
		log_messages.append("Checking raw data in case validation didn't run...")
		print("Checking raw data in case validation didn't run...")
		raw_response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix="raw/countries")
		if 'Contents' in raw_response:
			for obj in raw_response['Contents']:
				log_messages.append(f"  Raw: {obj['Key']}")
				print(f"  Raw: {obj['Key']}")
		
		raise Exception("No validated Parquet data found. Please ensure validation job completed successfully.")
	
	print(f"✓ Found {len(parquet_files)} Parquet files")
	log_messages.append(f"✓ Found {len(parquet_files)} Parquet files")
	for f in parquet_files:
		print(f"  - {f['Key']}")
		log_messages.append(f"  - {f['Key']}")
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
		print("Schema:")
		validated_df.printSchema()
	except Exception as e1:
		print(f"  Parquet read failed: {str(e1)}")
		log_messages.append(f"  Parquet read failed: {str(e1)}")
		raise
	
	log_messages.append("")
	
	# Step 3: Transform data
	print("Step 3: Transforming data...")
	log_messages.append("Step 3: Transforming data...")
	
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
	except Exception as e:
		print(f"⚠️ Error transforming data: {str(e)}")
		log_messages.append(f"⚠️ Error transforming data: {str(e)}")
		logger.exception("Transform error:")
		raise
	
	log_messages.append("")
	
	# Step 4: Write curated data
	print("Step 4: Writing curated data to S3 (partitioned by region)...")
	log_messages.append("Step 4: Writing curated data to S3 (partitioned by region)...")
	curated_path = f"s3://{bucket_name}/{curated_zone}/"
	print(f"  Writing to: {curated_path}")
	log_messages.append(f"  Writing to: {curated_path}")
	
	try:
		transformed_df.write \
			.mode("overwrite") \
			.format("parquet") \
			.option("compression", "snappy") \
			.partitionBy("region") \
			.save(curated_path)
		
		print(f"✓ Written {record_count} records to {curated_path}")
		log_messages.append(f"✓ Written {record_count} records to {curated_path}")
	except Exception as e:
		print(f"⚠️ Error writing curated data: {str(e)}")
		log_messages.append(f"⚠️ Error writing curated data: {str(e)}")
		logger.exception("Write error:")
		raise
	
	log_messages.append("")
	log_messages.append("=" * 60)
	log_messages.append("END: TRANSFORMATION JOB - SUCCESS")
	log_messages.append("=" * 60)
	log_messages.append(f"Summary: Records transformed: {record_count}")
	
	print("=" * 60)
	print("END: TRANSFORMATION JOB - SUCCESS")
	print("=" * 60)
	print(f"Summary: Records transformed: {record_count}")
	
	job.commit()
	log_messages.append("✓ Glue job committed")
	print("✓ Glue job committed")
	
	# Write log to S3
	log_content = "\n".join(log_messages)
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
	
	print("=" * 60)
	print(f"ERROR: {str(e)}")
	print("=" * 60)
	traceback.print_exc()
	
	log_content = "\n".join(log_messages)
	try:
		s3_client = boto3.client("s3")
		s3_client.put_object(
			Bucket=bucket_name,
			Key=f"logs/transformation_logs/transformation_error_{execution_timestamp}.log",
			Body=log_content.encode('utf-8')
		)
	except:
		pass
	
	sys.exit(1)