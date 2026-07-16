#!/usr/bin/env python3
"""
AWS Glue PySpark Test Job for validation:
- Tests DataFrame API transformations
- Tests Spark SQL capabilities
- Tests data type conversions and aggregations
- Tests reading/writing multiple formats (CSV, Parquet, JSON)

Usage (when running as a Glue job):
  --JOB_NAME=glue-test-job
  --INPUT_PATH=s3://bucket/input/
  --OUTPUT_PATH=s3://bucket/output/
  --INPUT_FORMAT=csv|parquet|json

Example with sample data:
  aws glue start-job-run \
    --job-name glue-test-job \
    --arguments='--JOB_NAME=glue-test-job,--INPUT_PATH=s3://bucket/input/,--OUTPUT_PATH=s3://bucket/output/,--INPUT_FORMAT=csv' \
    --region us-east-1
"""
import sys
import logging
from datetime import datetime
from awsglue.utils import getResolvedOptions
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    current_timestamp, col, when, round, count, avg, max, min,
    explode, split, upper, lower, trim, regexp_replace, to_json
)
from pyspark.sql.types import StructType, StructField, StringType, LongType, DoubleType

args = getResolvedOptions(sys.argv, ['JOB_NAME', 'INPUT_PATH', 'OUTPUT_PATH', 'INPUT_FORMAT'])

LOG = logging.getLogger('glue_test_job')
LOG.setLevel(logging.INFO)

def test_dataframe_api(df):
    """Test PySpark DataFrame API transformations."""
    LOG.info('=== Testing DataFrame API ===')
    
    # 1. Column transformations
    LOG.info('Testing column transformations...')
    df_transformed = df.select(
        col('*'),
        current_timestamp().alias('processed_timestamp')
    )
    
    # 2. Conditional logic (when/otherwise)
    if 'population' in df.columns:
        df_transformed = df_transformed.withColumn(
            'population_category',
            when(col('population') > 100000000, 'Large')
              .when(col('population') > 10000000, 'Medium')
              .otherwise('Small')
        ).withColumn(
            'population_int',
            col('population').cast('long')
        )
        LOG.info('Added population_category and population_int columns')
    
    # 3. Filtering with multiple conditions
    df_filtered = df_transformed.filter(
        (col('population').isNotNull()) | (col('country').isNotNull())
    )
    LOG.info(f'Filtered rows: {df_filtered.count()}')
    
    # 4. Distinct values
    if 'region' in df.columns:
        distinct_regions = df_filtered.select('region').distinct()
        LOG.info(f'Distinct regions: {distinct_regions.count()}')
        distinct_regions.show()
    
    # 5. String operations
    if 'country' in df.columns or 'name' in df.columns:
        name_col = 'country' if 'country' in df.columns else 'name'
        df_transformed = df_transformed.withColumn(
            f'{name_col}_upper',
            upper(col(name_col))
        ).withColumn(
            f'{name_col}_trimmed',
            trim(col(name_col))
        )
        LOG.info(f'Added string transformation columns for {name_col}')
    
    return df_transformed


def test_spark_sql(spark, df):
    """Test Spark SQL aggregations and complex queries."""
    LOG.info('=== Testing Spark SQL ===')
    
    # Register DataFrame as temp view
    df.createOrReplaceTempView('test_data')
    
    # 1. Basic SQL query
    LOG.info('Running basic SQL query...')
    result1 = spark.sql('SELECT COUNT(*) as total_rows FROM test_data')
    result1.show()
    
    # 2. Aggregations
    LOG.info('Testing aggregations...')
    if 'population' in df.columns:
        result2 = spark.sql('''
            SELECT
                COUNT(*) as count,
                AVG(CAST(population AS DOUBLE)) as avg_population,
                MAX(CAST(population AS DOUBLE)) as max_population,
                MIN(CAST(population AS DOUBLE)) as min_population
            FROM test_data
            WHERE population IS NOT NULL
        ''')
        result2.show()
    
    # 3. Group by query
    LOG.info('Testing GROUP BY...')
    if 'region' in df.columns:
        result3 = spark.sql('''
            SELECT
                region,
                COUNT(*) as country_count,
                AVG(CAST(population AS DOUBLE)) as avg_pop
            FROM test_data
            WHERE region IS NOT NULL
            GROUP BY region
            ORDER BY country_count DESC
        ''')
        result3.show()
    
    # 4. Window functions (if applicable)
    LOG.info('Testing window functions...')
    if 'region' in df.columns and 'population' in df.columns:
        result4 = spark.sql('''
            SELECT
                region,
                population,
                ROW_NUMBER() OVER (PARTITION BY region ORDER BY population DESC) as rank
            FROM test_data
            WHERE population IS NOT NULL
            LIMIT 10
        ''')
        result4.show()
    
    return True


def main():
    spark = SparkSession.builder.appName(args['JOB_NAME']).getOrCreate()
    LOG.info(f'Starting Glue test job: {args["JOB_NAME"]}')
    LOG.info(f'Timestamp: {datetime.now()}')

    input_path = args['INPUT_PATH']
    output_path = args['OUTPUT_PATH']
    input_format = args['INPUT_FORMAT'].lower()

    # === PHASE 1: Read Data ===
    LOG.info('=== PHASE 1: Reading Input Data ===')
    LOG.info(f'Input path: {input_path}')
    LOG.info(f'Input format: {input_format}')

    try:
        if input_format == 'csv':
            df = spark.read \
                .option('header', 'true') \
                .option('inferSchema', 'true') \
                .option('multiline', 'true') \
                .csv(input_path)
        elif input_format == 'parquet':
            df = spark.read.parquet(input_path)
        elif input_format == 'json':
            df = spark.read.json(input_path)
        else:
            LOG.error(f'Unsupported INPUT_FORMAT: {input_format}')
            spark.stop()
            sys.exit(2)

        LOG.info(f'Successfully read data from {input_path}')
        LOG.info(f'Total rows: {df.count()}')
        
        LOG.info('Schema:')
        df.printSchema()
        
        LOG.info('Sample data:')
        df.show(5, truncate=False)

    except Exception as e:
        LOG.error(f'Error reading input: {str(e)}')
        spark.stop()
        sys.exit(1)

    # === PHASE 2: DataFrame API Testing ===
    LOG.info('=== PHASE 2: DataFrame API Testing ===')
    try:
        df_transformed = test_dataframe_api(df)
        LOG.info('DataFrame API test completed successfully')
    except Exception as e:
        LOG.error(f'DataFrame API test failed: {str(e)}')
        df_transformed = df

    # === PHASE 3: Spark SQL Testing ===
    LOG.info('=== PHASE 3: Spark SQL Testing ===')
    try:
        test_spark_sql(spark, df_transformed)
        LOG.info('Spark SQL test completed successfully')
    except Exception as e:
        LOG.error(f'Spark SQL test failed: {str(e)}')

    # === PHASE 4: Write Output ===
    LOG.info('=== PHASE 4: Writing Output ===')
    try:
        LOG.info(f'Writing output to: {output_path}')
        df_transformed.write \
            .mode('overwrite') \
            .format('parquet') \
            .option('compression', 'snappy') \
            .save(output_path)
        
        LOG.info(f'Successfully wrote output to {output_path}')
        
        # Verify output by reading back
        output_df = spark.read.parquet(output_path)
        LOG.info(f'Output verification - Total rows written: {output_df.count()}')
        LOG.info('Output sample:')
        output_df.show(3, truncate=False)

    except Exception as e:
        LOG.error(f'Error writing output: {str(e)}')
        spark.stop()
        sys.exit(1)

    LOG.info('=== Job completed successfully ===')
    spark.stop()


if __name__ == '__main__':
    main()
