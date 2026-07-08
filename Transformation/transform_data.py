"""Final transformation job: read the intermediate parquet dataset and publish curated parquet data."""

import logging
import os
import sys
import traceback
from datetime import datetime

import boto3
from pyspark.sql import functions as F

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_runtime_args():
    """Read Glue job args when present, otherwise fall back to environment variables."""
    try:
        from awsglue.utils import getResolvedOptions
        return getResolvedOptions(sys.argv, ['JOB_NAME', 'TempDir', 'bucket_name', 'intermediate_zone', 'curated_zone'])
    except Exception:
        return {
            'bucket_name': os.environ.get('BUCKET_NAME', 'data-pipeline-country-population'),
            'intermediate_zone': os.environ.get('INTERMEDIATE_ZONE', 'intermediate/countries'),
            'curated_zone': os.environ.get('CURATED_ZONE', 'curated/countries'),
        }


def run_transformation(bucket_name, intermediate_zone, curated_zone, spark=None):
    execution_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    intermediate_path = f's3://{bucket_name}/{intermediate_zone}/'
    curated_path = f's3://{bucket_name}/{curated_zone}/'

    if spark is None:
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.appName('CuratedTransformationJob').getOrCreate()

    logger.info('Reading intermediate parquet data from %s', intermediate_path)
    intermediate_df = spark.read.parquet(intermediate_path)
    curated_df = intermediate_df.select(
        F.col('country_name'),
        F.col('region'),
        F.col('subregion'),
        F.col('population'),
        F.col('area'),
        F.col('capital_city'),
        F.col('currency'),
        F.current_date().alias('load_date'),
    )

    curated_df.write.mode('overwrite').format('parquet').option('compression', 'snappy').partitionBy('region').save(curated_path)

    s3_client = boto3.client('s3')
    log_content = '\n'.join([
        'TRANSFORMATION SUCCESS',
        '================',
        f'Timestamp: {execution_timestamp}',
        f'Curated path: {curated_path}',
        f'Records: {curated_df.count()}',
    ])
    s3_client.put_object(Bucket=bucket_name, Key=f'logs/transformation_logs/transformation_{execution_timestamp}.log', Body=log_content.encode('utf-8'))
    return curated_df


if __name__ == '__main__':
    args = get_runtime_args()
    try:
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.appName('CuratedTransformationJob').getOrCreate()
        run_transformation(
            bucket_name=args.get('bucket_name', 'data-pipeline-country-population'),
            intermediate_zone=args.get('intermediate_zone', 'intermediate/countries'),
            curated_zone=args.get('curated_zone', 'curated/countries'),
            spark=spark,
        )
    except Exception as exc:
        logger.error('Transformation job failed: %s', exc)
        logger.error(traceback.format_exc())
        sys.exit(1)
