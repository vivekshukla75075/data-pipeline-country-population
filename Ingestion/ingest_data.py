import requests
import json
import boto3
import os

def fetch_countries():
    url = "https://restcountries.com/v3.1/all"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def save_to_local(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def upload_to_s3(local_path, bucket, s3_key):
    s3 = boto3.client("s3")
    s3.upload_file(local_path, bucket, s3_key)

if __name__ == "__main__":
    data = fetch_countries()
    local_path = "countries_raw.json"
    save_to_local(data, local_path)
    # Optional: upload to S3
    bucket = os.environ.get("S3_BUCKET", "data-pipeline-country-population")
    upload_to_s3(local_path, bucket, "raw/countries/countries_raw.json")
