"""Lambda function to trigger ingestion job."""

import json
import boto3
import os
from datetime import datetime

glue_client = boto3.client("glue")
logger = None

def lambda_handler(event, context):
	"""Trigger Glue job for ingestion."""
	
	try:
		job_name = os.environ.get("GLUE_INGESTION_JOB", "country-population-ingestion")
		bucket_name = os.environ.get("S3_BUCKET", "data-pipeline-country-population")
		
		print(f"Triggering Glue job: {job_name}")
		
		response = glue_client.start_job_run(
			JobName=job_name,
			Arguments={
				"--bucket-name": bucket_name,
				"--job-bookmark-option": "job-bookmark-enable"
			}
		)
		
		job_run_id = response['JobRunId']
		print(f"✓ Ingestion job started with ID: {job_run_id}")
		
		return {
			"statusCode": 200,
			"body": json.dumps({
				"message": "Ingestion job triggered successfully",
				"job_run_id": job_run_id,
				"timestamp": datetime.utcnow().isoformat()
			})
		}
	
	except Exception as e:
		print(f"Error triggering ingestion job: {str(e)}")
		return {
			"statusCode": 500,
			"body": json.dumps({
				"error": str(e),
				"timestamp": datetime.utcnow().isoformat()
			})
		}
