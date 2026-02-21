"""Lambda function to trigger validation Glue job."""

import json
import boto3
import os
import time
from datetime import datetime

glue_client = boto3.client("glue")

def lambda_handler(event, context):
	"""Trigger Glue validation job."""
	
	try:
		job_name = os.environ.get("GLUE_VALIDATION_JOB", "country-population-validation")
		bucket_name = os.environ.get("S3_BUCKET", "data-pipeline-country-population")
		
		print(f"Triggering Glue job: {job_name}")
		
		response = glue_client.start_job_run(
			JobName=job_name,
			Arguments={
				"--bucket-name": bucket_name,
				"--raw-path": "raw/countries/",
				"--validated-path": "validated/countries/",
				"--job-bookmark-option": "job-bookmark-enable"
			}
		)
		
		job_run_id = response['JobRunId']
		print(f"✓ Validation job started with ID: {job_run_id}")
		
		# Wait for job completion
		max_wait_time = 600
		start_time = time.time()
		
		while time.time() - start_time < max_wait_time:
			job_run = glue_client.get_job_run(JobName=job_name, RunId=job_run_id)
			job_state = job_run['JobRun']['JobRunState']
			
			if job_state in ['SUCCEEDED', 'FAILED', 'STOPPED']:
				print(f"Job {job_state}: {job_run_id}")
				
				if job_state == 'SUCCEEDED':
					return {
						"statusCode": 200,
						"body": json.dumps({
							"message": "Validation job completed successfully",
							"job_run_id": job_run_id,
							"status": job_state,
							"timestamp": datetime.utcnow().isoformat()
						})
					}
				else:
					return {
						"statusCode": 500,
						"body": json.dumps({
							"error": f"Job failed with status: {job_state}",
							"job_run_id": job_run_id,
							"timestamp": datetime.utcnow().isoformat()
						})
					}
			
			time.sleep(5)
		
		return {
			"statusCode": 500,
			"body": json.dumps({
				"error": "Job execution timeout",
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
