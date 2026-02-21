"""Lambda function to execute Athena queries."""

import json
import boto3
import os
import time
from datetime import datetime

athena_client = boto3.client("athena")

def lambda_handler(event, context):
	"""Execute Athena query for analytics."""
	
	try:
		database = os.environ.get("ATHENA_DATABASE", "country_population")
		workgroup = os.environ.get("ATHENA_WORKGROUP", "primary")
		output_location = os.environ.get("ATHENA_OUTPUT_LOCATION", "s3://data-pipeline-country-population/athena-results/")
		
		# Example query
		query = """
		SELECT region, SUM(population) AS total_population, COUNT(*) AS country_count
		FROM countries_curated
		GROUP BY region
		ORDER BY total_population DESC
		"""
		
		print(f"Executing Athena query: {query}")
		
		response = athena_client.start_query_execution(
			QueryString=query,
			QueryExecutionContext={'Database': database},
			ResultConfiguration={'OutputLocation': output_location},
			WorkGroup=workgroup
		)
		
		query_execution_id = response['QueryExecutionId']
		print(f"✓ Athena query started with ID: {query_execution_id}")
		
		# Wait for query to complete
		max_attempts = 30
		for attempt in range(max_attempts):
			query_status = athena_client.get_query_execution(QueryExecutionId=query_execution_id)
			status = query_status['QueryExecution']['Status']['State']
			
			if status in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
				print(f"Query status: {status}")
				break
			
			time.sleep(2)
		
		if status == 'SUCCEEDED':
			result = athena_client.get_query_results(QueryExecutionId=query_execution_id)
			return {
				"statusCode": 200,
				"body": json.dumps({
					"message": "Athena query executed successfully",
					"results": result['ResultSet']['Rows'],
					"timestamp": datetime.utcnow().isoformat()
				})
			}
		else:
			return {
				"statusCode": 500,
				"body": json.dumps({
					"error": f"Query failed with status: {status}",
					"timestamp": datetime.utcnow().isoformat()
				})
			}
	
	except Exception as e:
		print(f"Error executing Athena query: {str(e)}")
		return {
			"statusCode": 500,
			"body": json.dumps({
				"error": str(e),
				"timestamp": datetime.utcnow().isoformat()
			})
		}
