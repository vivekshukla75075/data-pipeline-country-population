"""Lambda function to trigger validation job."""

import json
import boto3
import os
from datetime import datetime

glue_client = boto3.client("glue")

def lambda_handler(event, context):
	"""Trigger Glue job for validation."""
	
	try:
		# Get input from previous step
		ingestion_job_run_id = event.get('job_run_id')
		bucket_name = os.environ.get("S3_BUCKET", "data-pipeline-country-population")
		job_name = os.environ.get("GLUE_VALIDATION_JOB", "country-population-validation")
		
		print(f"Triggering validation job after ingestion run: {ingestion_job_run_id}")
		
		response = glue_client.start_job_run(
			JobName=job_name,
			Arguments={
				"--bucket-name": bucket_name,
				"--raw-path": "raw/countries/countries_raw.json",
				"--validated-path": "validated/countries/",
				"--job-bookmark-option": "job-bookmark-enable"
			}
		)
		
		job_run_id = response['JobRunId']
		print(f"✓ Validation job started with ID: {job_run_id}")
		
		return {
			"statusCode": 200,
			"body": json.dumps({
				"message": "Validation job triggered successfully",
				"job_run_id": job_run_id,
				"timestamp": datetime.utcnow().isoformat()
			})
		}
	
	except Exception as e:
		print(f"Error triggering validation job: {str(e)}")
		return {
			"statusCode": 500,
			"body": json.dumps({
				"error": str(e),
				"timestamp": datetime.utcnow().isoformat()
			})
		}
