"""Unit tests for validate_schema.py"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestSetupAwsInfrastructure:
	@patch("boto3.client")
	def test_create_bucket_success(self, mock_boto_client):
		"""Test successful S3 bucket creation."""
		mock_s3 = Mock()
		mock_iam = Mock()
		mock_boto_client.side_effect = lambda service: mock_s3 if service == "s3" else mock_iam
		
		from Validation.validate_schema import setup_aws_infrastructure
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
		
		from Validation.validate_schema import setup_aws_infrastructure
		setup_aws_infrastructure("test-bucket", "test-role")
		
		mock_iam.create_role.assert_called_once()


class TestRunValidation:
	@patch("Validation.validate_schema.SparkSession")
	def test_validation_filters_records(self, mock_spark_session):
		"""Test that validation filters records with population > 0."""
		mock_spark = Mock()
		mock_df = Mock()
		mock_df.filter.return_value = mock_df
		mock_df.count.return_value = 10
		
		mock_spark.read.json.return_value = mock_df
		mock_spark_session.builder.appName.return_value.getOrCreate.return_value = mock_spark
		
		from Validation.validate_schema import run_validation
		result = run_validation("test-bucket")
		
		assert result == 10
		mock_df.filter.assert_called_once()

	@patch("Validation.validate_schema.SparkSession")
	def test_validation_writes_parquet(self, mock_spark_session):
		"""Test that validation writes output to S3."""
		mock_spark = Mock()
		mock_df = Mock()
		mock_write = Mock()
		mock_df.filter.return_value = mock_df
		mock_df.write = mock_write
		mock_write.mode.return_value.parquet = Mock()
		mock_df.count.return_value = 5
		
		mock_spark.read.json.return_value = mock_df
		mock_spark_session.builder.appName.return_value.getOrCreate.return_value = mock_spark
		
		from Validation.validate_schema import run_validation
		run_validation("test-bucket")
		
		mock_write.mode.assert_called_with("overwrite")
