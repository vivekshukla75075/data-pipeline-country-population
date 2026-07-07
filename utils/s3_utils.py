"""S3 utilities for ETL pipeline."""

import boto3
from botocore.exceptions import ClientError
from utils.logger import setup_logger

logger = setup_logger(__name__)

class S3Utils:
	"""Utilities for S3 operations."""
	
	def __init__(self, region_name="us-east-1"):
		self.s3_client = boto3.client("s3", region_name=region_name)
	
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
		except ClientError as e:
			logger.exception(f"Failed to copy object: {str(e)}")
			return False
	
	def delete_object(self, bucket_name, key):
		"""Delete object from S3."""
		try:
			self.s3_client.delete_object(Bucket=bucket_name, Key=key)
			logger.info(f"✓ Deleted s3://{bucket_name}/{key}")
			return True
		except ClientError as e:
			logger.exception(f"Failed to delete object: {str(e)}")
			return False
	
	def list_objects(self, bucket_name, prefix):
		"""List objects in S3."""
		try:
			response = self.s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
			return response.get('Contents', [])
		except ClientError as e:
			logger.exception(f"Failed to list S3 objects: {str(e)}")
			return []
	
	def object_exists(self, bucket_name, key):
		"""Check if object exists in S3."""
		try:
			self.s3_client.head_object(Bucket=bucket_name, Key=key)
			return True
		except ClientError as e:
			if e.response['Error']['Code'] == '404':
				return False
			logger.exception(f"Error checking object: {str(e)}")
			return False
