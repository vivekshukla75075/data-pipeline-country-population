"""Lambda function to trigger transformation job."""

import json
import boto3
import os
from datetime import datetime

glue_client = boto3.client("glue")

def lambda_handler(event, context):
	"""Trigger Glue job for transformation."""
	
	try:
		bucket_name = os.environ.get("S3_BUCKET", "data-pipeline-country-population")
		job_name = os.environ.get("GLUE_TRANSFORMATION_JOB", "country-population-transformation")
		
		print(f"Triggering transformation job")
		
		response = glue_client.start_job_run(
			JobName=job_name,
			Arguments={
				"--bucket-name": bucket_name,
				"--validated-path": "validated/countries/",
				"--curated-path": "curated/countries/",
				"--job-bookmark-option": "job-bookmark-enable"
			}
		)
		
		job_run_id = response['JobRunId']
		print(f"✓ Transformation job started with ID: {job_run_id}")
		
		return {
			"statusCode": 200,
			"body": json.dumps({
				"message": "Transformation job triggered successfully",
				"job_run_id": job_run_id,
				"timestamp": datetime.utcnow().isoformat()
			})
		}
	
	except Exception as e:
		print(f"Error triggering transformation job: {str(e)}")
		return {
			"statusCode": 500,
			"body": json.dumps({
				"error": str(e),
				"timestamp": datetime.utcnow().isoformat()
			})
		}
