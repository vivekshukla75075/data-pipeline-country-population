"""Transformation: read validated data and produce curated parquet using AWS Glue.

Description:
- Reads validated parquet from S3 using AWS Glue
- Flattens fields and writes curated parquet partitioned by region
- Designed to run as AWS Glue PySpark job

Logs info and errors using the standard Python `logging` module.
"""

import argparse
import logging

logger = logging.getLogger(__name__)

def run_transformation(bucket_name="data-pipeline-country-population", validated_path="validated/countries/", curated_path="curated/countries/"):
	"""Run transformation job on AWS Glue using PySpark."""
	try:
		from awsglue.context import GlueContext
		from awsglue.job import Job
		from pyspark.context import SparkContext
		from pyspark.sql.functions import col
		
		# Initialize Glue context
		sc = SparkContext()
		glue_context = GlueContext(sc)
		spark = glue_context.spark_session
		job = Job(glue_context)
		
		validated_s3_path = f"s3://{bucket_name}/{validated_path}"
		curated_s3_path = f"s3://{bucket_name}/{curated_path}"
		
		logger.info("Reading validated data from %s", validated_s3_path)
		validated_df = spark.read.parquet(validated_s3_path)
		
		logger.info("Transforming data (flattening and selecting columns)")
		# ...existing code...
		transformed_df = validated_df.select(
			col("name.common").alias("country_name"),
			col("region"),
			col("population"),
			col("currencies").alias("currency_name")
		)
		
		logger.info("Writing curated data to %s partitioned by region", curated_s3_path)
		transformed_df.write.mode("overwrite").partitionBy("region").parquet(curated_s3_path)
		
		logger.info("Transformation completed successfully")
		job.commit()
		
		return transformed_df.count()
	except ImportError:
		logger.info("AWS Glue libraries not available. Using standard PySpark instead.")
		return run_transformation_spark(bucket_name, validated_path, curated_path)
	except Exception:
		logger.exception("Transformation job failed")
		raise

def run_transformation_spark(bucket_name="data-pipeline-country-population", validated_path="validated/countries/", curated_path="curated/countries/"):
	"""Fallback transformation using standard PySpark (for local testing)."""
	from pyspark.sql import SparkSession
	from pyspark.sql.functions import col

	try:
		spark = SparkSession.builder.appName("TransformationJob").getOrCreate()
		
		validated_s3_path = f"s3://{bucket_name}/{validated_path}"
		curated_s3_path = f"s3://{bucket_name}/{curated_path}"
		
		logger.info("Reading validated data from %s", validated_s3_path)
		validated_df = spark.read.parquet(validated_s3_path)
		
		logger.info("Transforming data (flattening and selecting columns)")
		transformed_df = validated_df.select(
			col("name.common").alias("country_name"),
			col("region"),
			col("population"),
			col("currencies").alias("currency_name")
		)
		
		logger.info("Writing curated data to %s partitioned by region", curated_s3_path)
		transformed_df.write.mode("overwrite").partitionBy("region").parquet(curated_s3_path)
		
		logger.info("Transformation completed successfully")
		return transformed_df.count()
	except Exception:
		logger.exception("Transformation job failed")
		raise

def main():
	parser = argparse.ArgumentParser(description="AWS Glue transformation job for country population data")
	parser.add_argument("--bucket-name", default=None, help="AWS S3 bucket name (default: data-pipeline-bucket)")
	parser.add_argument("--validated-path", default="validated/countries/", help="S3 path to validated parquet")
	parser.add_argument("--curated-path", default="curated/countries/", help="S3 path for curated parquet output")
	args = parser.parse_args()

	import os
	bucket_name = args.bucket_name or os.environ.get("S3_BUCKET", "data-pipeline-country-population")
	
	logger.info("Using S3 bucket: %s", bucket_name)
	logger.info("Running transformation job...")
	record_count = run_transformation(bucket_name, args.validated_path, args.curated_path)
	logger.info("Total transformed records: %d", record_count)

if __name__ == "__main__":
	main()