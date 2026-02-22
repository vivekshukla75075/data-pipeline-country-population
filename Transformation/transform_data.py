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
	
	# Step 1: Check validated data exists
	print("Step 1: Checking validated data in S3...")
	validated_path = f"s3://{bucket_name}/{validated_zone}/"
	print(f"  Checking: {validated_path}")
	
	data_exists = check_s3_data(bucket_name, validated_zone)
	
	if not data_exists:
		print("⚠️ No validated data found!")
		print("  Possible reasons:")
		print("    1. Validation job has not completed yet")
		print("    2. Validation job failed")
		print("    3. Data was not uploaded to validated zone")
		print("  Please run validation job first and wait for completion")
		raise Exception("No validated data found in S3")
	
	# Step 2: Read validated data
	print("Step 2: Reading validated data from S3...")
	print(f"  Reading from: {validated_path}")
	
	try:
		# Try reading as parquet first
		validated_df = spark.read.parquet(validated_path)
		record_count = validated_df.count()
		print(f"✓ Read {record_count} validated records (Parquet format)")
	except Exception as e1:
		print(f"  Parquet read failed: {str(e1)}")
		print("  Trying JSON format...")
		
		try:
			# Fallback to JSON if parquet fails
			validated_df = spark.read.json(validated_path)
			record_count = validated_df.count()
			print(f"✓ Read {record_count} validated records (JSON format)")
		except Exception as e2:
			print(f"  JSON read also failed: {str(e2)}")
			logger.exception("Data read errors:")
			raise Exception(f"Could not read validated data: Parquet({e1}), JSON({e2})")
	
	if record_count == 0:
		raise Exception("Validated data exists but contains 0 records")
	
	# Step 3: Transform data
	print("Step 3: Transforming data...")
	print(f"  Flattening nested columns...")
	
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
		print(f"  Schema: country_name, region, subregion, population, area, capital_city, currency")
	except Exception as e:
		print(f"⚠️ Error transforming data: {str(e)}")
		logger.exception("Transform error:")
		raise
	
	# Step 4: Write curated data (partitioned by region)
	print("Step 4: Writing curated data to S3 (partitioned by region)...")
	curated_path = f"s3://{bucket_name}/{curated_zone}/"
	print(f"  Writing to: {curated_path}")
	print(f"  Partitioning by: region")
	
	try:
		transformed_df.write \
			.mode("overwrite") \
			.format("parquet") \
			.option("compression", "snappy") \
			.partitionBy("region") \
			.save(curated_path)
		
		print(f"✓ Written {record_count} records to {curated_path}")
		print(f"✓ Data partitioned by region")
	except Exception as e:
		print(f"⚠️ Error writing curated data: {str(e)}")
		logger.exception("Write error:")
		raise
	
	print("=" * 60)
	print("END: TRANSFORMATION JOB - SUCCESS")
	print("=" * 60)
	print(f"Summary:")
	print(f"  Records transformed: {record_count}")
	print(f"  Output location: s3://{bucket_name}/{curated_zone}/")
	print(f"  Partitioned by: region")
	
	job.commit()
	print("✓ Glue job committed")
	
	print("=" * 60)
	print("NEXT STEPS:")
	print("  1. Check curated data in S3")
	print("  2. Query via Athena:")
	print("     SELECT region, COUNT(*) FROM country_population.countries_curated GROUP BY region;")
	print("=" * 60)

except Exception as e:
	print("=" * 60)
	print(f"ERROR: {str(e)}")
	print("=" * 60)
	import traceback
	traceback.print_exc()
	logger.exception("Transformation job failed:")
	
	print("")
	print("TROUBLESHOOTING:")
	print("  1. Check if validation job completed successfully")
	print("  2. Verify validated data exists in S3: s3://data-pipeline-country-population/validated/countries/")
	print("  3. Check Glue job logs in CloudWatch")
	print("  4. Run validation job again if data is missing")
	
	sys.exit(1)