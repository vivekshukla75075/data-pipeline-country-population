"""Lambda function to ingest data from REST Countries API and upload to S3."""

import json
import boto3
import urllib.request
from datetime import datetime

s3_client = boto3.client("s3")

def lambda_handler(event, context):
	"""Lambda handler for API ingestion."""
	
	try:
		print("=" * 60)
		print("START: API INGESTION LAMBDA")
		print("=" * 60)
		
		# Configuration
		api_url = "https://restcountries.com/v3.1/all"
		bucket_name = "data-pipeline-country-population"
		raw_zone = "raw/countries"
		timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		
		print(f"Configuration: API={api_url}, Bucket={bucket_name}")
		
		# Step 1: Fetch from API
		print("Step 1: Fetching from API...")
		request = urllib.request.Request(api_url, headers={'User-Agent': 'Lambda-ETL'})
		with urllib.request.urlopen(request, timeout=30) as response:
			data = json.loads(response.read().decode('utf-8'))
		
		print(f"✓ Fetched {len(data)} records from API")
		
		# Step 2: Prepare data
		print("Step 2: Preparing data...")
		filename = f"countries_raw_{timestamp}.json"
		json_data = json.dumps(data, indent=2)
		s3_key = f"{raw_zone}/{filename}"
		
		print(f"✓ Data prepared - {filename}")
		
		# Step 3: Upload to S3
		print("Step 3: Uploading to S3...")
		s3_client.put_object(
			Bucket=bucket_name,
			Key=s3_key,
			Body=json_data.encode('utf-8'),
			ContentType='application/json'
		)
		
		print(f"✓ Uploaded to s3://{bucket_name}/{s3_key}")
		
		print("=" * 60)
		print("END: API INGESTION LAMBDA - SUCCESS")
		print("=" * 60)
		
		return {
			"statusCode": 200,
			"body": json.dumps({
				"message": "Ingestion successful",
				"file": s3_key,
				"records": len(data),
				"timestamp": timestamp
			})
		}
	
	except Exception as e:
		print("=" * 60)
		print(f"ERROR: {str(e)}")
		print("=" * 60)
		
		import traceback
		traceback.print_exc()
		
		return {
			"statusCode": 500,
			"body": json.dumps({
				"error": str(e),
				"timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
			})
		}
