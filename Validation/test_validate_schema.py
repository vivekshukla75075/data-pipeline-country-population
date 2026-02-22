"""Unit tests for validation job."""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))


class TestValidationJob:
	"""Test validation job functions."""
	
	def test_validation_reads_raw_data(self):
		"""Test that validation reads raw data from S3."""
		from validate_schema import run_validation
		
		# Mock Spark
		mock_spark = MagicMock()
		mock_df = MagicMock()
		mock_df.count.return_value = 100
		mock_df.filter.return_value = mock_df
		mock_spark.read.json.return_value = mock_df
		
		# Mock S3
		with patch('validate_schema.boto3.client') as mock_s3:
			mock_s3_client = MagicMock()
			mock_s3.return_value = mock_s3_client
			mock_s3_client.list_objects_v2.return_value = {'Contents': []}
			
			glue_context = {'spark': mock_spark, 'job': None}
			result = run_validation(
				"test-bucket",
				"raw/countries",
				"validated/countries",
				"raw/countries_archive",
				glue_context
			)
			
			assert result >= 0
	
	def test_validation_filters_by_population(self):
		"""Test that validation filters records by population > 0."""
		from validate_schema import run_validation
		
		# Mock Spark
		mock_spark = MagicMock()
		mock_df = MagicMock()
		mock_filtered_df = MagicMock()
		
		mock_df.count.return_value = 100
		mock_filtered_df.count.return_value = 95  # 5 records filtered
		mock_df.filter.return_value = mock_filtered_df
		mock_spark.read.json.return_value = mock_df
		
		# Mock S3
		with patch('validate_schema.boto3.client') as mock_s3:
			mock_s3_client = MagicMock()
			mock_s3.return_value = mock_s3_client
			mock_s3_client.list_objects_v2.return_value = {'Contents': []}
			
			glue_context = {'spark': mock_spark, 'job': None}
			result = run_validation(
				"test-bucket",
				"raw/countries",
				"validated/countries",
				"raw/countries_archive",
				glue_context
			)
			
			assert result == 95
	
	def test_validation_writes_parquet(self):
		"""Test that validation writes data to parquet."""
		from validate_schema import run_validation
		
		# Mock Spark
		mock_spark = MagicMock()
		mock_df = MagicMock()
		mock_df.count.return_value = 100
		mock_df.filter.return_value = mock_df
		mock_df.write.mode.return_value = mock_df
		mock_spark.read.json.return_value = mock_df
		
		# Mock S3
		with patch('validate_schema.boto3.client') as mock_s3:
			mock_s3_client = MagicMock()
			mock_s3.return_value = mock_s3_client
			mock_s3_client.list_objects_v2.return_value = {'Contents': []}
			
			glue_context = {'spark': mock_spark, 'job': None}
			result = run_validation(
				"test-bucket",
				"raw/countries",
				"validated/countries",
				"raw/countries_archive",
				glue_context
			)
			
			# Verify parquet.write was called
			mock_df.write.mode.assert_called()
	
	def test_validation_archives_raw_files(self):
		"""Test that validation archives raw files."""
		from validate_schema import run_validation
		
		# Mock Spark
		mock_spark = MagicMock()
		mock_df = MagicMock()
		mock_df.count.return_value = 100
		mock_df.filter.return_value = mock_df
		mock_spark.read.json.return_value = mock_df
		
		# Mock S3
		with patch('validate_schema.boto3.client') as mock_s3:
			mock_s3_client = MagicMock()
			mock_s3.return_value = mock_s3_client
			
			# Mock list_objects_v2 to return files
			mock_s3_client.list_objects_v2.return_value = {
				'Contents': [
					{'Key': 'raw/countries/countries_raw_20240222_080241.json'}
				]
			}
			
			glue_context = {'spark': mock_spark, 'job': None}
			result = run_validation(
				"test-bucket",
				"raw/countries",
				"validated/countries",
				"raw/countries_archive",
				glue_context
			)
			
			# Verify copy_object and delete_object were called
			mock_s3_client.copy_object.assert_called()
			mock_s3_client.delete_object.assert_called()
