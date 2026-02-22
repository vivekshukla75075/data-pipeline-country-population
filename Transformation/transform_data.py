"""Transformation: Transform and partition country data using AWS Glue."""

import sys
import logging
import time
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
	from pyspark.sql.functions import col, when, lit, to_json, array, concat_wst
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
	
	# Step 2: Read validated data with retry logic
	print("Step 2: Reading validated data from S3...")
	log_messages.append("Step 2: Reading validated data from S3...")
	print(f"  Reading from: {validated_path}")
	log_messages.append(f"  Reading from: {validated_path}")
	
	max_retries = 3
	retry_delay = 5
	validated_df = None
	record_count = 0
	
	for attempt in range(max_retries):
		try:
			print(f"  Attempt {attempt + 1}/{max_retries}...")
			log_messages.append(f"  Attempt {attempt + 1}/{max_retries}...")
			
			# Add Hadoop configuration for better S3 handling
			spark.sparkContext._jsc.hadoopConfiguration().set("fs.s3a.connection.timeout", "30000")
			spark.sparkContext._jsc.hadoopConfiguration().set("fs.s3a.socket.timeout", "30000")
			spark.sparkContext._jsc.hadoopConfiguration().set("fs.s3a.attempts.maximum", "5")
			
			validated_df = spark.read.parquet(validated_path)
			record_count = validated_df.count()
			print(f"✓ Read {record_count} validated records (Parquet format)")
			log_messages.append(f"✓ Read {record_count} validated records (Parquet format)")
			print("Schema:")
			validated_df.printSchema()
			break
			
		except Exception as e:
			print(f"  Read attempt {attempt + 1} failed: {str(e)[:100]}...")
			log_messages.append(f"  Read attempt {attempt + 1} failed: {str(e)[:200]}...")
			
			if attempt < max_retries - 1:
				print(f"  Retrying in {retry_delay} seconds...")
				log_messages.append(f"  Retrying in {retry_delay} seconds...")
				time.sleep(retry_delay)
			else:
				print(f"All {max_retries} attempts failed")
				log_messages.append(f"All {max_retries} attempts failed")
				raise Exception(f"Failed to read Parquet data after {max_retries} attempts: {str(e)}")
	
	if validated_df is None:
		raise Exception("Could not read validated data")
	
	log_messages.append("")
	
	# Step 3: Transform data
	print("Step 3: Transforming data...")
	log_messages.append("Step 3: Transforming data...")
	
	try:
		# Display schema to understand data structureement or use null
		print("Input schema:") use null
		validated_df.printSchema()= validated_df.select(
		).alias("country_name"),
		# Transform with proper type handling
		transformed_df = validated_df.select(on"),
			# Extract country name
			col("name.common").alias("country_name"),
			# Direct columns# Get first element of capital array if it exists, otherwise null
			col("region"),")[0]).otherwise(None).alias("capital_city"),
			col("subregion"),l
			col("population"),").isNotNull(), col("currencies").cast("string")).otherwise(None).alias("currency")
			col("area"),
			# Handle capital array - get first element or null
			when({record_count} records")
				(col("capital").isNotNull()) & (size(col("capital")) > 0), Exception as e:
				col("capital")[0]	print(f"⚠️ Error transforming data: {str(e)}")
			).otherwise(lit("")).alias("capital_city"),⚠️ Error transforming data: {str(e)}")
			# Handle currencies - convert object to JSON string or empty string	logger.exception("Transform error:")
			when(col("currencies").isNotNull(), to_json(col("currencies")))
			.otherwise(lit("")).alias("currency")
		)
		
		print(f"✓ Transformed {record_count} records")
		log_messages.append(f"✓ Transformed {record_count} records")ed by region)...")
		print("Output schema:")log_messages.append("Step 4: Writing curated data to S3 (partitioned by region)...")
		transformed_df.printSchema()ted_path = f"s3://{bucket_name}/{curated_zone}/"
		curated_path}")
	except Exception as e:  Writing to: {curated_path}")
		print(f"⚠️ Error transforming data: {str(e)}")
		log_messages.append(f"⚠️ Error transforming data: {str(e)}")
		logger.exception("Transform error:")
		raise\
		.format("parquet") \
	log_messages.append("")
	
	# Step 4: Write curated data
	print("Step 4: Writing curated data to S3 (partitioned by region)...")
	log_messages.append("Step 4: Writing curated data to S3 (partitioned by region)...")
	curated_path = f"s3://{bucket_name}/{curated_zone}/"{record_count} records to {curated_path}")
	print(f"  Writing to: {curated_path}") Exception as e:
	log_messages.append(f"  Writing to: {curated_path}")	print(f"⚠️ Error writing curated data: {str(e)}")
	⚠️ Error writing curated data: {str(e)}")
	try:r:")
		transformed_df.write \
			.mode("overwrite") \
			.format("parquet") \
			.option("compression", "snappy") \log_messages.append("=" * 60)
			.partitionBy("region") \pend("END: TRANSFORMATION JOB - SUCCESS")
			.save(curated_path)
		pend(f"Summary: Records transformed: {record_count}")
		print(f"✓ Written {record_count} records to {curated_path}")
		log_messages.append(f"✓ Written {record_count} records to {curated_path}")print("=" * 60)
	except Exception as e:TRANSFORMATION JOB - SUCCESS")
		print(f"⚠️ Error writing curated data: {str(e)}")
		log_messages.append(f"⚠️ Error writing curated data: {str(e)}")sformed: {record_count}")
		logger.exception("Write error:")
		raise
	tted")
	log_messages.append("")mitted")
	log_messages.append("=" * 60)
	log_messages.append("END: TRANSFORMATION JOB - SUCCESS")
	log_messages.append("=" * 60)ges)
	log_messages.append(f"Summary: Records transformed: {record_count}")3_client.put_object(
			Bucket=bucket_name,
	print("=" * 60)ation_logs/transformation_{execution_timestamp}.log",
	print("END: TRANSFORMATION JOB - SUCCESS")e('utf-8')
	print("=" * 60)
	print(f"Summary: Records transformed: {record_count}")
	
	job.commit()end("")
	log_messages.append("✓ Glue job committed")
	print("✓ Glue job committed")log_messages.append(f"ERROR: {str(e)}")
	pend("=" * 60)
	# Write log to S3
	log_content = "\n".join(log_messages)pend(traceback.format_exc())
	s3_client.put_object(
		Bucket=bucket_name,print("=" * 60)
		Key=f"logs/transformation_logs/transformation_{execution_timestamp}.log",
		Body=log_content.encode('utf-8')t("=" * 60)
	)

except Exception as e:in(log_messages)
	log_messages.append("")
	log_messages.append("=" * 60)
	log_messages.append(f"ERROR: {str(e)}")3_client.put_object(
	log_messages.append("=" * 60)t=bucket_name,
	import traceback=f"logs/transformation_logs/transformation_error_{execution_timestamp}.log",
	log_messages.append(traceback.format_exc())		Body=log_content.encode('utf-8')
	

















	sys.exit(1)			pass	except:		)			Body=log_content.encode('utf-8')			Key=f"logs/transformation_logs/transformation_error_{execution_timestamp}.log",			Bucket=bucket_name,		s3_client.put_object(		s3_client = boto3.client("s3")	try:	log_content = "\n".join(log_messages)		traceback.print_exc()	print("=" * 60)	print(f"ERROR: {str(e)}")	print("=" * 60)	except:
		pass
	
	sys.exit(1)