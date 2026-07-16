"""Validation: validate raw country JSON and write a validated parquet dataset."""

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
        return getResolvedOptions(sys.argv, ['JOB_NAME', 'TempDir', 'bucket_name', 'raw_zone', 'validated_zone', 'archive_zone'])
    except Exception:
        return {
            'bucket_name': os.environ.get('BUCKET_NAME', 'data-pipeline-country-population'),
            'raw_zone': os.environ.get('RAW_ZONE', 'raw/countries'),
            'validated_zone': os.environ.get('VALIDATED_ZONE', 'validated/countries'),
            'archive_zone': os.environ.get('ARCHIVE_ZONE', 'archive/countries'),
        }


def run_validation(bucket_name, raw_zone, validated_zone, archive_zone, spark=None):
    """Validate raw records, write them to the validated layer and archive the raw files."""
    execution_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    raw_path = f's3://{bucket_name}/{raw_zone}/'
    validated_path = f's3://{bucket_name}/{validated_zone}/'

    if spark is None:
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.appName('ValidationJob').getOrCreate()

    logger.info('Reading raw data from %s', raw_path)
    raw_df = spark.read.option('multiline', 'true').json(raw_path)

    if '_corrupt_record' in raw_df.columns:
        logger.warning('Corrupt records found; the job will continue with the cleaned dataset.')

    # Extract the common name from the nested name object
    if 'name' in raw_df.columns:
        raw_df = raw_df.withColumn('name', F.col('name.common'))

    required_columns = ['name', 'population', 'region']
    missing_columns = [column for column in required_columns if column not in raw_df.columns]
    if missing_columns:
        raise ValueError(f'Missing required columns: {missing_columns}')

    validated_df = raw_df.filter(
        F.col('population').isNotNull() & (F.col('population') > 0) & F.col('region').isNotNull() & F.col('name').isNotNull()
    )

    record_count_raw = raw_df.count()
    record_count_validated = validated_df.count()
    logger.info('Validated %s of %s records', record_count_validated, record_count_raw)

    validated_df.write.mode('overwrite').format('parquet').option('compression', 'snappy').partitionBy('region').save(validated_path)

    s3_client = boto3.client('s3')
    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=raw_zone)
    archived_count = 0

    if 'Contents' in response:
        for obj in response['Contents']:
            key = obj['Key']
            if not key.endswith('.keep') and key.endswith('.json'):
                archive_key = key.replace(raw_zone, archive_zone)
                s3_client.copy_object(CopySource={'Bucket': bucket_name, 'Key': key}, Bucket=bucket_name, Key=archive_key)
                s3_client.delete_object(Bucket=bucket_name, Key=key)
                archived_count += 1

    log_content = '\n'.join([
        'VALIDATION SUCCESS',
        '================',
        f'Timestamp: {execution_timestamp}',
        f'Raw records: {record_count_raw}',
        f'Validated records: {record_count_validated}',
        f'Archived files: {archived_count}',
        f'Validated path: {validated_path}',
    ])
    s3_client.put_object(Bucket=bucket_name, Key=f'logs/validation_logs/validation_{execution_timestamp}.log', Body=log_content.encode('utf-8'))
    return record_count_validated


if __name__ == '__main__':
    args = get_runtime_args()
    try:
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.appName('ValidationJob').getOrCreate()
        run_validation(
            bucket_name=args.get('bucket_name', 'data-pipeline-country-population'),
            raw_zone=args.get('raw_zone', 'raw/countries'),
            validated_zone=args.get('validated_zone', 'validated/countries'),
            archive_zone=args.get('archive_zone', 'archive/countries'),
            spark=spark,
        )
    except Exception as exc:
        logger.error('Validation job failed: %s', exc)
        logger.error(traceback.format_exc())
        sys.exit(1)
