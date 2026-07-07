"""Glue utilities for ETL pipeline."""

import boto3
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class GlueUtils:
	"""Utilities for AWS Glue operations."""
	
	def __init__(self, region_name="us-east-1"):
		self.glue_client = boto3.client("glue", region_name=region_name)
	
	def create_database(self, database_name, description=""):
		"""Create Glue database."""
		try:
			self.glue_client.create_database(
				DatabaseInput={
					'Name': database_name,
					'Description': description
				}
			)
			logger.info(f"✓ Created Glue database: {database_name}")
			return True
		except self.glue_client.exceptions.AlreadyExistsException:
			logger.info(f"Database already exists: {database_name}")
			return True
		except Exception as e:
			logger.exception(f"Failed to create database: {str(e)}")
			return False
	
	def start_crawler(self, crawler_name):
		"""Start Glue Crawler."""
		try:
			self.glue_client.start_crawler(Name=crawler_name)
			logger.info(f"✓ Started Glue Crawler: {crawler_name}")
			return True
		except Exception as e:
			logger.exception(f"Failed to start crawler: {str(e)}")
			return False
	
	def get_crawler_status(self, crawler_name):
		"""Get Glue Crawler status."""
		try:
			response = self.glue_client.get_crawler(Name=crawler_name)
			return response['Crawler']['State']
		except Exception as e:
			logger.exception(f"Failed to get crawler status: {str(e)}")
			return None
