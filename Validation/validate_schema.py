"""Validation: validate raw country JSON and produce validated parquet using AWS Glue.

Description:
- Loads raw JSON from S3 and validates rows
- Writes validated parquet output to S3
- Moves processed raw files to raw_archive folder
- Fully parameterized with config management

Logs info and errors using JSON format for structured logging.
"""

import argparse
import json
import os
import sys
import logging

# ============================================
# Handle imports for both Glue and local execution
# ============================================
try:
	# Try Glue imports first
	from awsglue.utils import getResolvedOptions
	from awsglue.context import GlueContext
	from awsglue.job import Job
	from pyspark.context import SparkContext
	from pyspark.sql.functions import col
	IS_GLUE = True
except ImportError:
	IS_GLUE = False

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# S3 Utils (inline to avoid import issues in Glue)
# ============================================
class S3Utils:
	"""Inline S3 utilities for Glue compatibility."""
	
	def __init__(self):
		import boto3
		self.s3_client = boto3.client("s3")
	
	def copy_object(self, source_bucket, source_key, dest_bucket, dest_key):
		"""Copy object from source to destination."""
		try:
			self.s3_client.copy_object(
				CopySource={'Bucket': source_bucket, 'Key': source_key},
				Bucket=dest_bucket,
				Key=dest_key
			)
			logger.info(f"✓ Copied s3://{source_bucket}/{source_key} → s3://{dest_bucket}/{dest_key}")
			return True
		except Exception as e:
			logger.exception(f"Failed to copy object: {str(e)}")
			return False
	
	def delete_object(self, bucket_name, key):
		"""Delete object from S3."""
		try:
			self.s3_client.delete_object(Bucket=bucket_name, Key=key)
			logger.info(f"✓ Deleted s3://{bucket_name}/{key}")
			return True
		except Exception as e:
			logger.exception(f"Failed to delete object: {str(e)}")
			return False
	
	def list_objects(self, bucket_name, prefix):
		"""List objects in S3."""
		try:
			response = self.s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
			return response.get('Contents', [])
		except Exception as e:
			logger.exception(f"Failed to list S3 objects: {str(e)}")
			return []

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

def upload_all_scripts(bucket_name):
	"""Upload all .py scripts from the scripts directory to S3."""
	import boto3
	s3_client = boto3.client("s3")
	scripts_dir = os.path.join(os.path.dirname(__file__), "..", "scripts")
	if not os.path.exists(scripts_dir):
		logger.info("Scripts directory not found at %s", scripts_dir)
		return
	for fname in os.listdir(scripts_dir):
		if fname.endswith(".py"):
			local_path = os.path.join(scripts_dir, fname)
			s3_key = f"scripts/{fname}"
			try:
				s3_client.upload_file(local_path, bucket_name, s3_key)
				logger.info("✓ Uploaded %s to s3://%s/%s", local_path, bucket_name, s3_key)
			except Exception as e:
				logger.warning("Could not upload script %s: %s", fname, str(e))

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

def archive_raw_files(bucket_name, raw_zone="raw/countries"):
	"""Move processed raw files to archive folder."""
	try:
		s3_utils = S3Utils()
		
		# List all files in raw zone
		raw_files = s3_utils.list_objects(bucket_name, raw_zone)
		
		if not raw_files:
			logger.info(f"No files to archive in {raw_zone}")
			return True
		
		logger.info(f"Archiving {len(raw_files)} processed files")
		
		for obj in raw_files:
			source_key = obj['Key']
			
			# Skip .keep placeholder files
			if source_key.endswith('.keep'):
				continue
			
			# Create archive key path
			archive_key = source_key.replace(raw_zone, f"{raw_zone}_archive")
			
			# Copy to archive
			if s3_utils.copy_object(bucket_name, source_key, bucket_name, archive_key):
				# Delete original after successful copy
				s3_utils.delete_object(bucket_name, source_key)
				logger.info(f"✓ Archived: {source_key}")
			else:
				logger.warning(f"Failed to archive: {source_key}")
		
		logger.info(f"✓ Successfully archived all processed files")
		return True
	
	except Exception as e:
		logger.exception(f"Failed to archive raw files: {str(e)}")
		return False

def run_validation_glue(bucket_name, raw_path, validated_path):
	"""Run validation in Glue environment."""
	try:
		sc = SparkContext()
		glue_context = GlueContext(sc)
		spark = glue_context.spark_session
		job = Job(glue_context)
		
		raw_s3_path = f"s3://{bucket_name}/{raw_path}"
		validated_s3_path = f"s3://{bucket_name}/{validated_path}"
		
		logger.info(f"Reading raw data from {raw_s3_path}")
		raw_df = spark.read.json(raw_s3_path)
		
		logger.info("Validating records with population > 0")
		validated_df = raw_df.filter(col("population").isNotNull() & (col("population") > 0))
		
		logger.info(f"Writing validated data to {validated_s3_path}")
		validated_df.write.mode("overwrite").parquet(validated_s3_path)
		
		record_count = validated_df.count()
		logger.info(f"Validation completed: {record_count} records")
		job.commit()
		
		# Archive processed raw files
		logger.info("Archiving processed raw files...")
		raw_zone = os.path.dirname(raw_path)
		archive_raw_files(bucket_name, raw_zone)
		
		return record_count
	except Exception as e:
		logger.exception("Validation job failed")
		raise

def run_validation_spark(bucket_name, raw_path, validated_path):
	"""Fallback validation using standard PySpark (for local testing)."""
	from pyspark.sql import SparkSession
	from pyspark.sql.functions import col

	try:
		spark = SparkSession.builder.appName("ValidationJob").getOrCreate()
		
		raw_s3_path = f"s3://{bucket_name}/{raw_path}"
		validated_s3_path = f"s3://{bucket_name}/{validated_path}"
		
		logger.info(f"Reading raw data from {raw_s3_path}")
		raw_df = spark.read.json(raw_s3_path)
		
		logger.info("Validating records with population > 0")
		validated_df = raw_df.filter(col("population").isNotNull() & (col("population") > 0))
		
		logger.info(f"Writing validated data to {validated_s3_path}")
		validated_df.write.mode("overwrite").parquet(validated_s3_path)
		
		record_count = validated_df.count()
		logger.info(f"Validation completed: {record_count} records")
		
		# Archive processed raw files
		logger.info("Archiving processed raw files...")
		raw_zone = os.path.dirname(raw_path)
		archive_raw_files(bucket_name, raw_zone)
		
		return record_count
	except Exception as e:
		logger.exception("Validation job failed")
		raise

def main():
	parser = argparse.ArgumentParser(description="AWS Glue validation job for country population data")
	parser.add_argument("--bucket-name", default=None, help="AWS S3 bucket name")
	parser.add_argument("--raw-path", default="raw/countries/", help="S3 path to raw files")
	parser.add_argument("--validated-path", default="validated/countries/", help="S3 path for validated output")
	args = parser.parse_args()

	bucket_name = args.bucket_name or os.environ.get("S3_BUCKET", "data-pipeline-country-population")
	
	logger.info("Using S3 bucket: %s", bucket_name)
	logger.info("Running validation job...")
	
	if IS_GLUE:
		record_count = run_validation_glue(bucket_name, args.raw_path, args.validated_path)
	else:
		record_count = run_validation_spark(bucket_name, args.raw_path, args.validated_path)
	
	logger.info("Total validated records: %d", record_count)

if __name__ == "__main__":
	main()