"""S3 utilities for ETL pipeline."""

import boto3
from botocore.exceptions import ClientError
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class S3Utils:
	"""Utilities for S3 operations."""
	
	def __init__(self, region_name="us-east-1"):
		self.s3_client = boto3.client("s3", region_name=region_name)
	
	def check_bucket_exists(self, bucket_name):
		"""Check if bucket exists."""
		try:
			self.s3_client.head_bucket(Bucket=bucket_name)
			logger.info(f"✓ S3 bucket exists: {bucket_name}")
			return True
		except ClientError as e:
			if e.response['Error']['Code'] == '404':
				logger.warning(f"S3 bucket does not exist: {bucket_name}")
				return False
			raise
	
	def upload_file(self, local_path, bucket_name, s3_key):
		"""Upload file to S3."""
		try:
			self.s3_client.upload_file(local_path, bucket_name, s3_key)
			logger.info(f"✓ Uploaded to S3: s3://{bucket_name}/{s3_key}")
			return True
		except Exception as e:
			logger.exception(f"Failed to upload to S3: {str(e)}")
			return False
	
	def list_objects(self, bucket_name, prefix):
		"""List objects in S3."""
		try:
			response = self.s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
			return response.get('Contents', [])
		except Exception as e:
			logger.exception(f"Failed to list S3 objects: {str(e)}")
			return []
