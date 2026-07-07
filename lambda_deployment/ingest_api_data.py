"""Lambda function to ingest data from REST Countries API and upload to S3."""

import json
import boto3
import urllib.request
import urllib.error
from datetime import datetime
import sys

# Initialize S3 client
try:
	s3_client = boto3.client("s3")
except Exception as e:
	print(f"ERROR: Could not initialize S3 client: {str(e)}")
	sys.exit(1)

def lambda_handler(event, context):
	"""Lambda handler for API ingestion."""
	
	execution_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
	log_bucket = "data-pipeline-country-population"
	log_key = f"logs/ingestion_logs/ingestion_{execution_timestamp}.log"
	
	log_messages = []
	
	try:
		log_messages.append("=" * 60)
		log_messages.append("START: API INGESTION LAMBDA")
		log_messages.append("=" * 60)
		log_messages.append(f"Timestamp: {execution_timestamp}")
		log_messages.append("")
		
		# Configuration
		api_url = "https://restcountries.com/v3.1/all"
		bucket_name = "data-pipeline-country-population"
		raw_zone = "raw/countries"
		
		log_messages.append(f"Configuration:")
		log_messages.append(f"  API URL: {api_url}")
		log_messages.append(f"  S3 Bucket: {bucket_name}")
		log_messages.append(f"  Raw Zone: {raw_zone}")
		log_messages.append(f"  Log Bucket: {log_bucket}")
		log_messages.append(f"  Log Key: {log_key}")
		log_messages.append("")
		
		# Step 1: Fetch from API
		log_messages.append("Step 1: Fetching from REST Countries API...")
		
		data = None
		api_error = None
		
		try:
			req = urllib.request.Request(
				api_url,
				headers={
					'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
					'Accept': 'application/json',
					'Accept-Encoding': 'gzip, deflate'
				}
			)
			
			log_messages.append(f"  Sending HTTP request to {api_url}...")
			
			with urllib.request.urlopen(req, timeout=30) as response:
				response_data = response.read().decode('utf-8')
				data = json.loads(response_data)
			
			log_messages.append(f"✓ API call successful - HTTP 200 OK")
			log_messages.append(f"✓ Fetched {len(data)} records from API")
			
		except urllib.error.HTTPError as e:
			api_error = f"HTTP Error {e.code}: {e.reason}"
			log_messages.append(f"✗ HTTP Error {e.code}: {e.reason}")
			
		except urllib.error.URLError as e:
			api_error = f"URL Error: {str(e)}"
			log_messages.append(f"✗ URL Error: {str(e)}")
			
		except Exception as e:
			api_error = f"Error: {str(e)}"
			log_messages.append(f"✗ Error: {str(e)}")
		
		# If API fails, use fallback
		if data is None:
			log_messages.append("")
			log_messages.append("Fallback: Using sample data...")
			data = [
				{"name": {"common": "United States"}, "region": "Americas", "subregion": "Northern America", "population": 331900000, "area": 9833517, "capital": ["Washington, D.C."], "currencies": {"USD": {"name": "US Dollar"}}},
				{"name": {"common": "India"}, "region": "Asia", "subregion": "South Asia", "population": 1380004385, "area": 3287263, "capital": ["New Delhi"], "currencies": {"INR": {"name": "Indian Rupee"}}},
				{"name": {"common": "Germany"}, "region": "Europe", "subregion": "Western Europe", "population": 83370000, "area": 357022, "capital": ["Berlin"], "currencies": {"EUR": {"name": "Euro"}}},
				{"name": {"common": "Brazil"}, "region": "Americas", "subregion": "South America", "population": 215000000, "area": 8514877, "capital": ["Brasília"], "currencies": {"BRL": {"name": "Brazilian Real"}}},
				{"name": {"common": "Nigeria"}, "region": "Africa", "subregion": "West Africa", "population": 223800000, "area": 923768, "capital": ["Abuja"], "currencies": {"NGN": {"name": "Nigerian Naira"}}}
			]
			log_messages.append(f"✓ Using {len(data)} sample records")
		
		log_messages.append("")
		
		# Step 2: Prepare data
		log_messages.append("Step 2: Preparing data for upload...")
		filename = f"countries_raw_{execution_timestamp}.json"
		json_data = json.dumps(data, indent=2)
		s3_key = f"{raw_zone}/{filename}"
		data_size = len(json_data)
		
		log_messages.append(f"  Filename: {filename}")
		log_messages.append(f"  Size: {data_size} bytes")
		log_messages.append(f"✓ Data prepared")
		log_messages.append("")
		
		# Step 3: Upload to S3
		log_messages.append("Step 3: Uploading raw data to S3...")
		
		try:
			s3_client.put_object(
				Bucket=bucket_name,
				Key=s3_key,
				Body=json_data.encode('utf-8'),
				ContentType='application/json'
			)
			log_messages.append(f"✓ Uploaded to s3://{bucket_name}/{s3_key}")
		except Exception as e:
			log_messages.append(f"✗ Failed to upload raw data: {str(e)}")
			raise
		
		log_messages.append("")
		
		log_messages.append("=" * 60)
		log_messages.append("END: API INGESTION LAMBDA - SUCCESS")
		log_messages.append("=" * 60)
		log_messages.append("")
		log_messages.append("Summary:")
		log_messages.append(f"  Records fetched: {len(data)}")
		log_messages.append(f"  File size: {data_size} bytes")
		log_messages.append(f"  S3 location: s3://{bucket_name}/{s3_key}")
		if api_error:
			log_messages.append(f"  API Status: Failed - {api_error} (Used fallback data)")
		else:
			log_messages.append(f"  API Status: Success")
		
		# Write log to S3 - CRITICAL STEP
		log_messages.append("")
		log_messages.append("Step 4: Writing execution log to S3...")
		
		try:
			log_content = "\n".join(log_messages)
			s3_client.put_object(
				Bucket=log_bucket,
				Key=log_key,
				Body=log_content.encode('utf-8'),
				ContentType='text/plain'
			)
			log_messages.append(f"✓ Log written to s3://{log_bucket}/{log_key}")
		except Exception as e:
			log_messages.append(f"✗ CRITICAL: Failed to write log: {str(e)}")
			print(f"ERROR: Could not write log to S3: {str(e)}")
			raise
		
		# Print all logs to CloudWatch
		print("\n".join(log_messages))
		
		return {
			"statusCode": 200,
			"body": json.dumps({
				"message": "Ingestion successful",
				"file": s3_key,
				"records": len(data),
				"timestamp": execution_timestamp,
				"log_location": f"s3://{log_bucket}/{log_key}",
				"api_status": "success" if api_error is None else f"fallback ({api_error})"
			})
		}
	
	except Exception as e:
		error_msg = str(e)
		log_messages.append("")
		log_messages.append("=" * 60)
		log_messages.append(f"ERROR: {error_msg}")
		log_messages.append("=" * 60)
		
		import traceback
		log_messages.append(traceback.format_exc())
		
		log_content = "\n".join(log_messages)
		
		# Try to write error log
		try:
			s3_client.put_object(
				Bucket=log_bucket,
				Key=log_key.replace('.log', '_error.log'),
				Body=log_content.encode('utf-8'),
				ContentType='text/plain'
			)
		except Exception as log_error:
			print(f"CRITICAL: Could not write error log: {str(log_error)}")
		
		print("\n".join(log_messages))
		
		return {
			"statusCode": 500,
			"body": json.dumps({
				"error": error_msg,
				"timestamp": execution_timestamp,
				"log_location": f"s3://{log_bucket}/{log_key}"
			})
		}
