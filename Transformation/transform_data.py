"""Transformation: read validated data and produce curated parquet using AWS Glue.

Description:
- Reads validated parquet from S3
- Flattens and transforms fields
- Writes curated parquet partitioned by region
- Fully parameterized with config management

Logs info and errors using JSON format for structured logging.
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import get_config
from utils.logger import setup_logger

logger = setup_logger(__name__)

def run_transformation(bucket_name, validated_path, curated_path):
	"""Run transformation job on AWS Glue using PySpark."""
	try:
		from awsglue.context import GlueContext
		from awsglue.job import Job
		from pyspark.context import SparkContext
		from pyspark.sql.functions import col, explode, when
		
		sc = SparkContext()
		glue_context = GlueContext(sc)
		spark = glue_context.spark_session
		job = Job(glue_context)
		
		validated_s3_path = f"s3://{bucket_name}/{validated_path}"
		curated_s3_path = f"s3://{bucket_name}/{curated_path}"
		
		logger.info(f"Reading validated data from {validated_s3_path}")
		validated_df = spark.read.parquet(validated_s3_path)
		
		logger.info("Transforming data (flattening and selecting columns)")
		transformed_df = validated_df.select(
			col("name.common").alias("country_name"),
			col("region"),
			col("subregion"),
			col("population"),
			col("area"),
			col("capital").alias("capital_city"),
			when(col("currencies").isNotNull(), explode(col("currencies"))).otherwise(None).alias("currency")
		).dropDuplicates()
		
		logger.info(f"Writing curated data to {curated_s3_path} partitioned by region")
		transformed_df.write.mode("overwrite").partitionBy("region").parquet(curated_s3_path)
		
		record_count = transformed_df.count()
		logger.info(f"Transformation completed successfully: {record_count} records")
		job.commit()
		
		return record_count
	except ImportError:
		logger.info("AWS Glue libraries not available. Using standard PySpark instead.")
		return run_transformation_spark(bucket_name, validated_path, curated_path)
	except Exception:
		logger.exception("Transformation job failed")
		raise

def run_transformation_spark(bucket_name="data-pipeline-country-population", validated_path="validated/countries/", curated_path="curated/countries/"):
	"""Fallback transformation using standard PySpark (for local testing)."""
	from pyspark.sql import SparkSession
	from pyspark.sql.functions import col, explode, when

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
			col("subregion"),
			col("population"),
			col("area"),
			col("capital").alias("capital_city"),
			when(col("currencies").isNotNull(), explode(col("currencies"))).otherwise(None).alias("currency")
		).dropDuplicates()
		
		logger.info("Writing curated data to %s partitioned by region", curated_s3_path)
		transformed_df.write.mode("overwrite").partitionBy("region").parquet(curated_s3_path)
		
		logger.info("Transformation completed successfully")
		return transformed_df.count()
	except Exception:
		logger.exception("Transformation job failed")
		raise

def main():
	parser = argparse.ArgumentParser(description="AWS Glue transformation job for country population data")
	parser.add_argument("--bucket-name", default=None, help="AWS S3 bucket name (default: data-pipeline-country-population)")
	parser.add_argument("--validated-path", default="validated/countries/", help="S3 path to validated parquet")
	parser.add_argument("--curated-path", default="curated/countries/", help="S3 path for curated parquet output")
	args = parser.parse_args()

	bucket_name = args.bucket_name or os.environ.get("S3_BUCKET", "data-pipeline-country-population")
	
	logger.info("Using S3 bucket: %s", bucket_name)
	logger.info("Running transformation job...")
	record_count = run_transformation(bucket_name, args.validated_path, args.curated_path)
	logger.info("Total transformed records: %d", record_count)

if __name__ == "__main__":
	main()