"""Lambda function to create Glue Data Catalog tables."""

import json
import boto3
import os
from datetime import datetime

glue_client = boto3.client("glue")

def lambda_handler(event, context):
	"""Create or update Glue Data Catalog tables."""
	
	try:
		database_name = os.environ.get("GLUE_DATABASE", "country_population")
		bucket_name = os.environ.get("S3_BUCKET", "data-pipeline-country-population")
		
		# Create database if not exists
		try:
			glue_client.create_database(
				DatabaseInput={'Name': database_name}
			)
			print(f"✓ Created Glue database: {database_name}")
		except glue_client.exceptions.AlreadyExistsException:
			print(f"Database already exists: {database_name}")
		
		# Create curated table
		glue_client.create_table(
			DatabaseName=database_name,
			TableInput={
				'Name': 'countries_curated',
				'StorageDescriptor': {
					'Columns': [
						{'Name': 'country_name', 'Type': 'string'},
						{'Name': 'region', 'Type': 'string'},
						{'Name': 'subregion', 'Type': 'string'},
						{'Name': 'population', 'Type': 'bigint'},
						{'Name': 'area', 'Type': 'double'},
						{'Name': 'capital_city', 'Type': 'string'},
						{'Name': 'currency', 'Type': 'string'}
					],
					'Location': f's3://{bucket_name}/curated/countries/',
					'InputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat',
					'OutputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat',
					'SerdeInfo': {
						'SerializationLibrary': 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'
					}
				},
				'PartitionKeys': [{'Name': 'region', 'Type': 'string'}],
				'TableType': 'EXTERNAL_TABLE'
			}
		)
		
		print("✓ Created Glue Data Catalog table: countries_curated")
		
		return {
			"statusCode": 200,
			"body": json.dumps({
				"message": "Glue Data Catalog created successfully",
				"timestamp": datetime.utcnow().isoformat()
			})
		}
	
	except Exception as e:
		print(f"Error creating Glue catalog: {str(e)}")
		return {
			"statusCode": 500,
			"body": json.dumps({
				"error": str(e),
				"timestamp": datetime.utcnow().isoformat()
			})
		}
