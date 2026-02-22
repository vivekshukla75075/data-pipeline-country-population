"""Transformation: Transform and partition country data using AWS Glue."""

import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("=" * 60)
print("START: TRANSFORMATION JOB")
print("=" * 60)

try:
	from awsglue.utils import getResolvedOptions
	from awsglue.context import GlueContext
	from awsglue.job import Job
	from pyspark.context import SparkContext
	from pyspark.sql.functions import col, coalesce
	
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
	
	# Step 1: Read validated data
	print("Step 1: Reading validated data from S3...")
	validated_path = f"s3://{bucket_name}/{validated_zone}/"
	validated_df = spark.read.parquet(validated_path)
	record_count = validated_df.count()
	print(f"✓ Read {record_count} validated records")
	
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
	transformed_df.write.mode("overwrite").parquet(curated_path, partitionBy="region")
	print(f"✓ Written to {curated_path} (partitioned by region)")
	
	print("=" * 60)
	print("END: TRANSFORMATION JOB - SUCCESS")
	print("=" * 60)
	
	job.commit()

except Exception as e:
	print("=" * 60)
	print(f"ERROR: {str(e)}")
	print("=" * 60)
	import traceback
	traceback.print_exc()
	sys.exit(1)