"""Ingestion: fetch country data from REST API and store raw JSON files.

Description:
- Fetches data from restcountries.com
- Writes a timestamped file to `output/raw/countries/`
- Keeps a latest copy at `output/countries_raw.json` for compatibility
- Optionally uploads files to S3 using `utils.s3_helper.upload_to_s3`

Logs info and errors using the standard Python `logging` module.
"""

import requests
import json
import os
import sys
import datetime
import logging

# Ensure project root is on sys.path so `utils` package can be imported when
# running this script directly
root = os.path.dirname(os.path.dirname(__file__))
if root not in sys.path:
    sys.path.insert(0, root)

from utils.s3_helper import upload_to_s3

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")

def fetch_api_data():
    url = "https://restcountries.com/v3.1/all"
    params = {
        "fields": "name,region,population,capital"
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def main():
    data = fetch_api_data()
    root = os.path.join(os.path.dirname(__file__), "..")
    output_dir = os.path.join(root, "output")
    raw_dir = os.path.join(output_dir, "raw", "countries")
    os.makedirs(raw_dir, exist_ok=True)

    # timestamped filename for appendable raw files
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = f"countries_raw_{timestamp}.json"
    raw_file = os.path.join(raw_dir, filename)
    try:
        with open(raw_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        logger.exception("Failed to write timestamped raw file %s", raw_file)
        raise

    # Also keep a latest copy at the previous top-level path for compat
    latest_file = os.path.join(output_dir, "countries_raw.json")
    try:
        with open(latest_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        logger.exception("Failed to write latest raw file %s", latest_file)
        raise

    logger.info("Successfully fetched %d countries from API", len(data))
    logger.info("Timestamped data saved to %s", raw_file)
    logger.info("Latest copy saved to %s", latest_file)

    # Upload to S3 raw zone (optional, may fail without AWS credentials)
    try:
        # upload the timestamped file and also update the latest copy
        upload_to_s3(raw_file, f"raw/countries/{filename}")
        upload_to_s3(latest_file, "raw/countries/countries_raw.json")
    except Exception:
        logger.exception("S3 upload skipped or failed")

if __name__ == "__main__":
    main()