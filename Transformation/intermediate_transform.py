"""Intermediate transformation job: build parquet data for the next curated stage."""

import logging
import os
import sys
import traceback
from datetime import datetime

import boto3
from pyspark.sql import functions as F

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def list_parquet_files(bucket_name, prefix):
    """List existing parquet files under an S3 prefix."""
    s3_client = boto3.client('s3')
    prefix = prefix.rstrip('/') + '/'
    paginator = s3_client.get_paginator('list_objects_v2')
    parquet_files = []

    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        for obj in page.get('Contents', []):
            key = obj['Key']
            if key.endswith('.parquet'):
                parquet_files.append(f's3://{bucket_name}/{key}')

    return parquet_files


def get_runtime_args():
    """Read Glue job args when present, otherwise fall back to environment variables."""
    try:
        from awsglue.utils import getResolvedOptions
        return getResolvedOptions(sys.argv, ['JOB_NAME', 'TempDir', 'bucket_name', 'validated_zone', 'intermediate_zone'])
    except Exception:
        return {
            'bucket_name': os.environ.get('BUCKET_NAME', 'data-pipeline-country-population'),
            'validated_zone': os.environ.get('VALIDATED_ZONE', 'validated/countries'),
            'intermediate_zone': os.environ.get('INTERMEDIATE_ZONE', 'intermediate/countries'),
        }


def run_intermediate_transform(bucket_name, validated_zone, intermediate_zone, spark=None):
    execution_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_path = f's3://{bucket_name}/{validated_zone}/'
    output_path = f's3://{bucket_name}/{intermediate_zone}/'

    if spark is None:
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.appName('IntermediateTransformationJob').getOrCreate()

    logger.info('Listing validated parquet files under %s', base_path)
    parquet_files = list_parquet_files(bucket_name, validated_zone)
    if not parquet_files:
        raise ValueError(f'No validated parquet files found under {base_path}')

    logger.info('Found %s validated parquet file(s) to read.', len(parquet_files))
    validated_df = spark.read.parquet(*parquet_files)

    intermediate_df = validated_df.select(
        F.col('name.common').alias('country_name'),
        F.col('region'),
        F.col('subregion'),
        F.col('population').cast('long').alias('population'),
        F.col('area').cast('double').alias('area'),
        F.when(F.col('capital').isNotNull() & (F.size(F.col('capital')) > 0), F.col('capital')[0])
         .otherwise(F.lit('')).alias('capital_city'),
        F.when(F.col('currencies').isNotNull(), F.to_json(F.col('currencies')))
         .otherwise(F.lit('')).alias('currency'),
    )

    intermediate_df.write.mode('overwrite').format('parquet').partitionBy('region').save(output_path)

    s3_client = boto3.client('s3')
    log_content = f"Intermediate transformation completed at {execution_timestamp}"
    s3_client.put_object(
        Bucket=bucket_name,
        Key=f'logs/intermediate_logs/intermediate_{execution_timestamp}.log',
        Body=log_content.encode('utf-8'),
    )

    return intermediate_df


if __name__ == '__main__':
    args = get_runtime_args()
    spark = None
    try:
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.appName('IntermediateTransformationJob').getOrCreate()
        run_intermediate_transform(
            bucket_name=args.get('bucket_name', 'data-pipeline-country-population'),
            validated_zone=args.get('validated_zone', 'validated/countries'),
            intermediate_zone=args.get('intermediate_zone', 'intermediate/countries'),
            spark=spark,
        )
    except Exception as exc:
        logger.error('Intermediate transformation failed: %s', exc)
        logger.error(traceback.format_exc())
        sys.exit(1)
