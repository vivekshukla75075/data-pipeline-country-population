"""Unit tests for validate_schema.py"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestSetupAwsInfrastructure:
	@patch("boto3.client")
	def test_create_bucket_success(self, mock_boto_client):
		"""Test successful S3 bucket creation."""
		mock_s3 = Mock()
		mock_iam = Mock()
		mock_boto_client.side_effect = lambda service: mock_s3 if service == "s3" else mock_iam
		
		from validate_schema import setup_aws_infrastructure
		setup_aws_infrastructure("test-bucket", "test-role")
		
		mock_s3.create_bucket.assert_called_once_with(Bucket="test-bucket")
		mock_iam.create_role.assert_called_once()

	@patch("boto3.client")
	def test_bucket_already_exists(self, mock_boto_client):
		"""Test handling of existing bucket."""
		mock_s3 = Mock()
		mock_iam = Mock()
		mock_boto_client.side_effect = lambda service: mock_s3 if service == "s3" else mock_iam
		mock_s3.create_bucket.side_effect = mock_s3.exceptions.BucketAlreadyOwnedByYou()
		
		from validate_schema import setup_aws_infrastructure
		setup_aws_infrastructure("test-bucket", "test-role")
		
		mock_iam.create_role.assert_called_once()


class TestRunValidation:
	@patch("pyspark.sql.functions.col")
	@patch("pyspark.sql.SparkSession")
	def test_validation_filters_records(self, mock_spark_session, mock_col):
		"""Test that validation filters records with population > 0."""
		mock_spark = Mock()
		mock_df = Mock()
		mock_filter_result = Mock()
		
		# Setup col mock
		mock_col.return_value = MagicMock()
		
		# Setup DataFrame mocks
		mock_df.filter.return_value = mock_filter_result
		mock_filter_result.count.return_value = 10
		
		mock_spark.read.json.return_value = mock_df
		mock_spark_session.builder.appName.return_value.getOrCreate.return_value = mock_spark
		
		from validate_schema import run_validation
		result = run_validation("test-bucket")
		
		assert result == 10
		mock_df.filter.assert_called_once()

	@patch("pyspark.sql.functions.col")
	@patch("pyspark.sql.SparkSession")
	def test_validation_writes_parquet(self, mock_spark_session, mock_col):
		"""Test that validation writes output to S3."""
		mock_spark = Mock()
		mock_df = Mock()
		mock_filter_result = Mock()
		mock_write = Mock()
		mock_mode_result = Mock()
		
		# Setup col mock
		mock_col.return_value = MagicMock()
		
		# Setup DataFrame chain mocks
		mock_df.filter.return_value = mock_filter_result
		mock_filter_result.write = mock_write
		mock_write.mode.return_value = mock_mode_result
		mock_filter_result.count.return_value = 5
		
		mock_spark.read.json.return_value = mock_df
		mock_spark_session.builder.appName.return_value.getOrCreate.return_value = mock_spark
		
		from validate_schema import run_validation
		run_validation("test-bucket")
		
		mock_write.mode.assert_called_with("overwrite")
		mock_mode_result.parquet.assert_called_once()
