"""Transformation: Transform and partition country data using AWS Glue."""

import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("=" * 60)
print("START: TRANSFORMATION JOB")
print("=" * 60)

def ensure_s3_paths(bucket_name):
	"""Ensure required S3 paths exist."""
	import boto3
	s3_client = boto3.client("s3")
	
	paths_to_create = [
		f"{bucket_name}/validated/countries/.keep",
		f"{bucket_name}/curated/countries/.keep"
	]
	
	for path in paths_to_create:
		bucket_name_only = path.split('/')[0]
		key = '/'.join(path.split('/')[1:])
		
		try:
			s3_client.put_object(Bucket=bucket_name_only, Key=key, Body=b"")
			print(f"✓ Ensured path: s3://{path}")
		except Exception as e:
			print(f"⚠️ Could not create path {path}: {str(e)}")

try:
	from awsglue.utils import getResolvedOptions
	from awsglue.context import GlueContext
	from awsglue.job import Job
	from pyspark.context import SparkContext
	from pyspark.sql.functions import col, coalesce
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
	validated_zone = "validated/countries"
	curated_zone = "curated/countries"
	
	print(f"Configuration: Bucket={bucket_name}")
	print(f"  Validated Zone: {validated_zone}")
	print(f"  Curated Zone: {curated_zone}")
	
	# Ensure S3 paths exist
	print("Step 0: Ensuring S3 paths exist...")
	ensure_s3_paths(bucket_name)
	
	# Step 1: Read validated data
	print("Step 1: Reading validated data from S3...")
	validated_path = f"s3://{bucket_name}/{validated_zone}/"
	print(f"  Reading from: {validated_path}")
	
	try:
		validated_df = spark.read.parquet(validated_path)
		record_count = validated_df.count()
		print(f"✓ Read {record_count} validated records")
	except Exception as e:
		print(f"⚠️ No validated data found or error reading: {str(e)}")
		logger.exception("Validated data read error:")
		sys.exit(1)
	
	# Step 2: Transform data
	print("Step 2: Transforming data...")
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
	
	# Step 3: Write curated data (partitioned by region)
	print("Step 3: Writing curated data to S3 (partitioned by region)...")
	curated_path = f"s3://{bucket_name}/{curated_zone}/"
	print(f"  Writing to: {curated_path}")
	
	try:
		transformed_df.write \
			.mode("overwrite") \
			.format("parquet") \
			.option("compression", "snappy") \
			.partitionBy("region") \
			.save(curated_path)
		
		print(f"✓ Written {record_count} records to {curated_path} (partitioned by region)")
	except Exception as e:
		print(f"⚠️ Error writing curated data: {str(e)}")
		logger.exception("Write error:")
		raise
	
	print("=" * 60)
	print("END: TRANSFORMATION JOB - SUCCESS")
	print("=" * 60)
	print(f"Summary:")
	print(f"  Records transformed: {record_count}")
	print(f"  Output partitioned by: region")
	
	job.commit()
	print("✓ Glue job committed")

except Exception as e:
	print("=" * 60)
	print(f"ERROR: {str(e)}")
	print("=" * 60)
	import traceback
	traceback.print_exc()
	logger.exception("Transformation job failed:")
	sys.exit(1)