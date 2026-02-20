"""Validation: validate raw country JSON and produce validated parquet.

Description:
- Loads raw JSON from S3 and validates rows (population present and > 0)
- Writes validated parquet output to S3 (overwrites existing validated output)
- Creates AWS S3 bucket and IAM role/policies for Spark jobs on demand

Logs info and errors using the standard Python `logging` module.
"""

import argparse
import logging
import json

logger = logging.getLogger(__name__)

def setup_aws_infrastructure(bucket_name="my-bucket", role_name="spark-validation-role"):
	"""Create S3 bucket and IAM role with necessary policies for Spark jobs."""
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
	
	# Create IAM role
	assume_role_policy = {
		"Version": "2012-10-17",
		"Statement": [
			{
				"Effect": "Allow",
				"Principal": {"Service": "ec2.amazonaws.com"},
				"Action": "sts:AssumeRole"
			}
		]
	}
	
	try:
		iam_client.create_role(
			RoleName=role_name,
			AssumeRolePolicyDocument=json.dumps(assume_role_policy),
			Description="Role for Spark validation jobs"
		)
		logger.info("Created IAM role: %s", role_name)
	except iam_client.exceptions.EntityAlreadyExistsException:
		logger.info("IAM role already exists: %s", role_name)
	except Exception as e:
		logger.warning("Could not create IAM role (may already exist or insufficient permissions): %s. Error: %s", role_name, str(e))
	
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
			PolicyName="S3AccessPolicy",
			PolicyDocument=json.dumps(s3_policy)
		)
		logger.info("Attached S3 access policy to role: %s", role_name)
	except Exception as e:
		logger.warning("Could not attach S3 policy to role (may lack permissions): %s. Error: %s", role_name, str(e))

def run_validation(bucket_name="my-bucket", raw_path="raw/countries/countries_raw.json", validated_path="validated/countries/"):
	"""Run validation job on AWS using Spark."""
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
	parser = argparse.ArgumentParser(description="AWS-based validation job for country population data")
	parser.add_argument("--setup-aws", action="store_true", help="Create AWS S3 bucket and IAM role before running validation")
	parser.add_argument("--bucket-name", default="my-bucket", help="AWS S3 bucket name (default: my-bucket)")
	parser.add_argument("--role-name", default="spark-validation-role", help="IAM role name (default: spark-validation-role)")
	parser.add_argument("--raw-path", default="raw/countries/countries_raw.json", help="S3 path to raw JSON file")
	parser.add_argument("--validated-path", default="validated/countries/", help="S3 path for validated parquet output")
	args = parser.parse_args()

	if args.setup_aws:
		logger.info("Setting up AWS infrastructure (bucket and IAM role)...")
		setup_aws_infrastructure(args.bucket_name, args.role_name)
		logger.info("AWS infrastructure setup completed (may have skipped due to permissions)")

	logger.info("Running validation job...")
	record_count = run_validation(args.bucket_name, args.raw_path, args.validated_path)
	logger.info("Total validated records: %d", record_count)

if __name__ == "__main__":
	main()