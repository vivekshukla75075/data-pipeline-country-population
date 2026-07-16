#!/usr/bin/env python3
"""
Simple AWS Glue PySpark job for testing:
- Reads CSV or Parquet from S3
- Performs small transformations using DataFrame / Spark SQL
- Writes output back to S3 (Parquet)

Usage (when running as a Glue job): pass JOB_NAME, INPUT_PATH, OUTPUT_PATH, INPUT_FORMAT
Example input formats: csv or parquet
"""
import sys
import logging
from awsglue.utils import getResolvedOptions
from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp, col

args = getResolvedOptions(sys.argv, ['JOB_NAME', 'INPUT_PATH', 'OUTPUT_PATH', 'INPUT_FORMAT'])

LOG = logging.getLogger('glue_test_job')
LOG.setLevel(logging.INFO)

def main():
    spark = SparkSession.builder.appName(args['JOB_NAME']).getOrCreate()
    LOG.info('Starting Glue test job')

    input_path = args['INPUT_PATH']
    output_path = args['OUTPUT_PATH']
    input_format = args['INPUT_FORMAT'].lower()

    LOG.info('Reading input: %s (format=%s)', input_path, input_format)
    if input_format == 'csv':
        df = spark.read.option('header', 'true').option('inferSchema', 'true').csv(input_path)
    elif input_format == 'parquet':
        df = spark.read.parquet(input_path)
    else:
        LOG.error('Unsupported INPUT_FORMAT: %s', input_format)
        spark.stop()
        sys.exit(2)

    LOG.info('Input schema:')
    df.printSchema()
    LOG.info('Input sample:')
    df.show(5, truncate=False)

    # Small transformation examples
    # 1) Add ingest timestamp
    df2 = df.withColumn('ingest_ts', current_timestamp())

    # 2) Normalize a numeric column if present (example: population -> population_int)
    if 'population' in df2.columns:
        df2 = df2.withColumn('population_int', col('population').cast('long'))

    # 3) Simple filter example
    if 'country' in df2.columns:
        df2 = df2.filter(col('country').isNotNull())

    LOG.info('Transformed sample:')
    df2.show(5, truncate=False)

    # Save output as partitioned parquet for easy verification
    LOG.info('Writing output to %s', output_path)
    df2.write.mode('overwrite').parquet(output_path)

    LOG.info('Job finished successfully')
    spark.stop()


if __name__ == '__main__':
    main()
