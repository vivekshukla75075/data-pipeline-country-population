"""Validation: validate raw country JSON and produce validated parquet using AWS Glue.

Description:
- Loads raw JSON from S3 and validates rows (population present and > 0)
- Writes validated parquet output to S3 (overwrites existing validated output)
- Designed to run as AWS Glue PySpark job
- Creates AWS S3 bucket and IAM role/policies for Glue jobs on demand

Logs info and errors using the standard Python `logging` module.
"""

import argparse
import logging
import json
import os

logger = logging.getLogger(__name__)

def check_and_create_bucket(bucket_name):
	"""Check if bucket exists, create if it doesn't."""
	import boto3
	
	s3_client = boto3.client("s3")
	
	try:
		s3_client.head_bucket(Bucket=bucket_name)
		logger.info("✓ S3 bucket exists: %s", bucket_name)
		return True
	except s3_client.exceptions.NoSuchBucket:
		logger.info("Bucket does not exist: %s. Attempting to create...", bucket_name)
		try:
			s3_client.create_bucket(Bucket=bucket_name)
			logger.info("✓ Created S3 bucket: %s", bucket_name)
			return True
		except Exception as e:
			logger.warning("Could not create bucket (insufficient permissions): %s", str(e))
			return False
	except Exception as e:
		logger.warning("Could not verify bucket: %s", str(e))
		return False

def upload_file_to_s3(local_path, bucket_name, s3_key):
	"""Upload a file to S3."""
	import boto3
	
	s3_client = boto3.client("s3")
	
	try:
		s3_client.upload_file(local_path, bucket_name, s3_key)
		logger.info("✓ Uploaded %s to s3://%s/%s", local_path, bucket_name, s3_key)
		return True
	except Exception as e:
		logger.warning("Could not upload %s to S3: %s", local_path, str(e))
		return False

def setup_aws_infrastructure(bucket_name="data-pipeline-country-population", role_name="glue-validation-role"):
	"""Create S3 bucket and IAM role with necessary policies for Glue jobs."""
	import boto3
	
	s3_client = boto3.client("s3")
	iam_client = boto3.client("iam")
	
	# Create S3 bucket
	try:
		s3_client.create_bucket(Bucket=bucket_name)
		logger.info("Created S3 bucket: %s", bucket_name)
	except s3_client.exceptions.BucketAlreadyOwnedByYou:
		logger.info("S3 bucket already exists: %s", bucket_name)
	except s3_client.exceptions.BucketAlreadyExists:
		logger.info("S3 bucket already exists (owned by another account): %s", bucket_name)
	except Exception as e:
		logger.warning("Could not create S3 bucket (may already exist or insufficient permissions): %s. Error: %s", bucket_name, str(e))
	
	# Create IAM role for Glue
	assume_role_policy = {
		"Version": "2012-10-17",
		"Statement": [
			{
				"Effect": "Allow",
				"Principal": {"Service": "glue.amazonaws.com"},
				"Action": "sts:AssumeRole"
			}
		]
	}
	
	try:
		iam_client.create_role(
			RoleName=role_name,
			AssumeRolePolicyDocument=json.dumps(assume_role_policy),
			Description="Role for AWS Glue validation jobs"
		)
		logger.info("Created IAM role for Glue: %s", role_name)
	except iam_client.exceptions.EntityAlreadyExistsException:
		logger.info("IAM role already exists: %s", role_name)
	except Exception as e:
		logger.warning("Could not create IAM role: %s. Error: %s", role_name, str(e))
	
	# Attach S3 policy to role
	s3_policy = {
		"Version": "2012-10-17",
		"Statement": [
			{
				"Effect": "Allow",
				"Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
				"Resource": f"arn:aws:s3:::{bucket_name}/*"
			},
			{
				"Effect": "Allow",
				"Action": ["s3:ListBucket"],
				"Resource": f"arn:aws:s3:::{bucket_name}"
			}
		]
	}
	
	try:
		iam_client.put_role_policy(
			RoleName=role_name,
			PolicyName="S3AccessPolicy_datapipeline",
			PolicyDocument=json.dumps(s3_policy)
		)
		logger.info("Attached S3 access policy to Glue role: %s", role_name)
	except Exception as e:
		logger.warning("Could not attach S3 policy: %s. Error: %s", role_name, str(e))

def ensure_s3_directories(bucket_name):
	"""Ensure S3 directories exist by uploading a placeholder file to each."""
	import boto3
	s3_client = boto3.client("s3")
	paths = [
		"raw/countries/.keep",
		"validated/countries/.keep",
		"curated/countries/.keep"
	]
	for path in paths:
		try:
			s3_client.put_object(Bucket=bucket_name, Key=path, Body=b"")
			logger.info("Ensured S3 directory: s3://%s/%s", bucket_name, path)
		except Exception as e:
			logger.warning("Could not ensure S3 directory %s: %s", path, str(e))

def upload_ingestion_script(bucket_name):
	"""Upload ingestion script to S3 if present."""
	import boto3
	s3_client = boto3.client("s3")
	local_path = os.path.join(os.path.dirname(__file__), "..", "Ingestion", "ingest_data.py")
	s3_key = "scripts/ingest_data.py"
	if os.path.exists(local_path):
		try:
			s3_client.upload_file(local_path, bucket_name, s3_key)
			logger.info("✓ Uploaded ingestion script to s3://%s/%s", bucket_name, s3_key)
		except Exception as e:
			logger.warning("Could not upload ingestion script: %s", str(e))
	else:
		logger.info("Ingestion script not found at %s", local_path)

def run_validation(bucket_name="data-pipeline-country-population", raw_path="raw/countries/countries_raw.json", validated_path="validated/countries/"):
	"""Run validation job on AWS Glue using PySpark."""
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
		
		raw_s3_path = f"s3://{bucket_name}/{raw_path}"
		validated_s3_path = f"s3://{bucket_name}/{validated_path}"
		
		logger.info("Reading raw data from %s", raw_s3_path)
		raw_df = spark.read.json(raw_s3_path)
		
		logger.info("Validating records with population > 0")
		validated_df = raw_df.filter(col("population").isNotNull() & (col("population") > 0))
		
		logger.info("Writing validated data to %s", validated_s3_path)
		validated_df.write.mode("overwrite").parquet(validated_s3_path)
		
		logger.info("Validation completed successfully")
		record_count = validated_df.count()
		job.commit()
		
		return record_count
	except ImportError:
		logger.info("AWS Glue libraries not available. Using standard PySpark instead.")
		return run_validation_spark(bucket_name, raw_path, validated_path)
	except Exception:
		logger.exception("Validation job failed")
		raise

def run_validation_spark(bucket_name="data-pipeline-country-population", raw_path="raw/countries/countries_raw.json", validated_path="validated/countries/"):
	"""Fallback validation using standard PySpark (for local testing)."""
	from pyspark.sql import SparkSession
	from pyspark.sql.functions import col

	try:
		spark = SparkSession.builder.appName("ValidationJob").getOrCreate()
		
		raw_s3_path = f"s3://{bucket_name}/{raw_path}"
		validated_s3_path = f"s3://{bucket_name}/{validated_path}"
		
		logger.info("Reading raw data from %s", raw_s3_path)
		raw_df = spark.read.json(raw_s3_path)
		
		logger.info("Validating records with population > 0")
		validated_df = raw_df.filter(col("population").isNotNull() & (col("population") > 0))
		
		logger.info("Writing validated data to %s", validated_s3_path)
		validated_df.write.mode("overwrite").parquet(validated_s3_path)
		
		logger.info("Validation completed successfully")
		return validated_df.count()
	except Exception:
		logger.exception("Validation job failed")
		raise

def main():
	parser = argparse.ArgumentParser(description="AWS Glue validation job for country population data")
	parser.add_argument("--setup-aws", action="store_true", help="Create AWS S3 bucket and IAM role before running validation")
	parser.add_argument("--bucket-name", default=None, help="AWS S3 bucket name (default: data-pipeline-country-population)")
	parser.add_argument("--role-name", default="glue-validation-role", help="IAM role name (default: glue-validation-role)")
	parser.add_argument("--raw-path", default="raw/countries/countries_raw.json", help="S3 path to raw JSON file")
	parser.add_argument("--validated-path", default="validated/countries/", help="S3 path for validated parquet output")
	args = parser.parse_args()

	# Use environment variable or command-line argument for bucket name
	bucket_name = args.bucket_name or os.environ.get("S3_BUCKET", "data-pipeline-country-population")
	role_name = args.role_name
	
	logger.info("Using S3 bucket: %s", bucket_name)
	logger.info("Using IAM role: %s", role_name)

	if args.setup_aws:
		logger.info("Setting up AWS infrastructure (bucket and IAM role)...")
		setup_aws_infrastructure(bucket_name, role_name)
		logger.info("AWS infrastructure setup completed")
		ensure_s3_directories(bucket_name)
		upload_ingestion_script(bucket_name)

	logger.info("Running validation job...")
	record_count = run_validation(bucket_name, args.raw_path, args.validated_path)
	logger.info("Total validated records: %d", record_count)

	# Glue job instructions
	logger.info("To create the Glue job, use:")
	logger.info("Job name: country-population-validation")
	logger.info("IAM Role: glue-validation-role")
	logger.info("Script location: s3://%s/scripts/validate_schema.py", bucket_name)
	logger.info("Arguments: --bucket-name %s --raw-path raw/countries/countries_raw.json --validated-path validated/countries/", bucket_name)

if __name__ == "__main__":
	main()