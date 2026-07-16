import boto3
import json
from botocore.exceptions import ClientError

REGION = 'us-east-1'
WORKGROUP = 'primary'
RESULT_BUCKET = 's3://data-pipeline-dev-778277577996/athena-results/'
DATABASE = 'default'
TABLE = 'curated_countries'
LOCATION = 's3://data-pipeline-dev-778277577996/curated/countries/'

athena = boto3.client('athena', region_name=REGION)
glue = boto3.client('glue', region_name=REGION)


def ensure_workgroup():
    try:
        athena.get_work_group(WorkGroup=WORKGROUP)
        print(f'Workgroup {WORKGROUP} already exists')
    except ClientError as e:
        if e.response['Error']['Code'] == 'InvalidRequestException':
            athena.create_work_group(
                Name=WORKGROUP,
                Configuration={
                    'ResultConfiguration': {
                        'OutputLocation': RESULT_BUCKET,
                    }
                },
                Description='Primary Athena workgroup for pipeline queries'
            )
            print(f'Created workgroup {WORKGROUP}')
        else:
            raise

    athena.update_work_group(
        WorkGroup=WORKGROUP,
        State='ENABLED',
        Description='Primary Athena workgroup for pipeline queries',
        Configuration={
            'ResultConfiguration': {
                'OutputLocation': RESULT_BUCKET,
            }
        }
    )
    print(f'Updated workgroup {WORKGROUP} with result location {RESULT_BUCKET}')


def ensure_database():
    try:
        glue.get_database(Name=DATABASE)
        print(f'Database {DATABASE} already exists')
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityNotFoundException':
            glue.create_database(
                DatabaseInput={
                    'Name': DATABASE,
                    'Description': 'Database for country population pipeline data'
                }
            )
            print(f'Created database {DATABASE}')
        else:
            raise


def ensure_table():
    try:
        glue.get_table(DatabaseName=DATABASE, Name=TABLE)
        print(f'Table {DATABASE}.{TABLE} already exists')
        return
    except ClientError as e:
        if e.response['Error']['Code'] != 'EntityNotFoundException':
            raise

    glue.create_table(
        DatabaseName=DATABASE,
        TableInput={
            'Name': TABLE,
            'Description': 'Curated country population data in parquet',
            'TableType': 'EXTERNAL_TABLE',
            'Parameters': {
                'classification': 'parquet',
                'typeOfData': 'file'
            },
            'StorageDescriptor': {
                'Columns': [
                    {'Name': 'country_name', 'Type': 'string'},
                    {'Name': 'subregion', 'Type': 'string'},
                    {'Name': 'population', 'Type': 'bigint'},
                    {'Name': 'area', 'Type': 'double'},
                    {'Name': 'capital_city', 'Type': 'string'},
                    {'Name': 'currency', 'Type': 'string'},
                    {'Name': 'load_date', 'Type': 'date'}
                ],
                'Location': LOCATION,
                'InputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat',
                'OutputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat',
                'SerdeInfo': {
                    'SerializationLibrary': 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'
                }
            },
            'PartitionKeys': [
                {'Name': 'region', 'Type': 'string'}
            ]
        }
    )
    print(f'Created table {DATABASE}.{TABLE}')


def add_partitions():
    regions = ['Africa', 'Americas', 'Antarctic', 'Asia', 'Europe', 'Oceania']
    for region in regions:
        try:
            glue.create_partition(
                DatabaseName=DATABASE,
                TableName=TABLE,
                PartitionInput={
                    'Values': [region],
                    'StorageDescriptor': {
                        'Columns': [
                            {'Name': 'country_name', 'Type': 'string'},
                            {'Name': 'subregion', 'Type': 'string'},
                            {'Name': 'population', 'Type': 'bigint'},
                            {'Name': 'area', 'Type': 'double'},
                            {'Name': 'capital_city', 'Type': 'string'},
                            {'Name': 'currency', 'Type': 'string'},
                            {'Name': 'load_date', 'Type': 'date'}
                        ],
                        'Location': f'{LOCATION}region={region}/',
                        'InputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat',
                        'OutputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat',
                        'SerdeInfo': {
                            'SerializationLibrary': 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'
                        }
                    }
                }
            )
            print(f'Added partition for {region}')
        except ClientError as e:
            if e.response['Error']['Code'] != 'AlreadyExistsException':
                raise
            print(f'Partition already exists for {region}')


if __name__ == '__main__':
    ensure_workgroup()
    ensure_database()
    ensure_table()
    add_partitions()
    print('Athena setup completed successfully.')
