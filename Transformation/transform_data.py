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
		print(f"  Parquet read failed, trying JSON...")
		log_messages.append(f"  Parquet read failed, trying JSON...")
		
		try:
			validated_df = spark.read.json(validated_path)
			record_count = validated_df.count()
			print(f"✓ Read {record_count} validated records (JSON format)")
			log_messages.append(f"✓ Read {record_count} validated records (JSON format)")
		except Exception as e2:
			error_msg = f"Could not read validated data"
			print(error_msg)
			log_messages.append(error_msg)
			raise Exception(error_msg)
	
	log_messages.append("")
	
	# Step 3: Transform data
	print("Step 3: Transforming data...")
	log_messages.append("Step 3: Transforming data...")
	
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
	log_messages.append("")
	
	# Step 4: Write curated data
	print("Step 4: Writing curated data to S3 (partitioned by region)...")
	log_messages.append("Step 4: Writing curated data to S3 (partitioned by region)...")
	curated_path = f"s3://{bucket_name}/{curated_zone}/"
	print(f"  Writing to: {curated_path}")
	log_messages.append(f"  Writing to: {curated_path}")
	
	transformed_df.write \
		.mode("overwrite") \
		.format("parquet") \
		.option("compression", "snappy") \
		.partitionBy("region") \
		.save(curated_path)
	
	print(f"✓ Written {record_count} records to {curated_path}")
	log_messages.append(f"✓ Written {record_count} records to {curated_path}")
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
	s3_client = boto3.client("s3")
	s3_client.put_object(
		Bucket=bucket_name,
		Key=f"logs/transformation_logs/transformation_error_{execution_timestamp}.log",
		Body=log_content.encode('utf-8')
	)
	
	sys.exit(1)