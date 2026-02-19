"""Local runner for validation + transformation (pandas/pyarrow).

Description:
- Reads raw JSON from `output/` (or `RAW_FILE` env var)
- Writes validated parquet and transformed curated parquet (overwrites existing)
- Uses logging (info/error) for observability
"""

import os
import json
import pandas as pd
import shutil
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")

root = os.path.dirname(os.path.dirname(__file__))
raw_file = os.environ.get("RAW_FILE") or os.path.join(root, "output", "countries_raw.json")
validated_dir = os.environ.get("VALIDATED_DIR") or os.path.join(root, "output", "validated", "countries")
validated_path = os.environ.get("VALIDATED_PATH")
curated_dir = os.environ.get("CURATED_DIR") or os.path.join(root, "output", "curated", "countries")
curated_path = os.environ.get("CURATED_PATH")

os.makedirs(validated_dir, exist_ok=True)
os.makedirs(curated_dir, exist_ok=True)

logger.info("Reading raw data from %s", raw_file)
try:
    with open(raw_file, "r", encoding="utf-8") as f:
        data = json.load(f)
except Exception:
    logger.exception("Failed to read raw file %s", raw_file)
    raise

# Normalize JSON to flat table
df = pd.json_normalize(data)

# Basic validation: population must be present and > 0
df_valid = df[df["population"].notna() & (df["population"] > 0)].copy()
logger.info("Validated rows: %d", len(df_valid))

df_valid.to_parquet(validated_path, engine="pyarrow", index=False)
# Save validated parquet
if validated_path:
    # remove existing if present
    if os.path.exists(validated_path):
        if os.path.isdir(validated_path):
            shutil.rmtree(validated_path)
        else:
            os.remove(validated_path)
    df_valid.to_parquet(validated_path, engine="pyarrow", index=False)
    logger.info("Saved validated parquet to %s", validated_path)
else:
    validated_path_local = os.path.join(validated_dir, "validated.parquet")
    if os.path.exists(validated_path_local):
        os.remove(validated_path_local)
    df_valid.to_parquet(validated_path_local, engine="pyarrow", index=False)
    logger.info("Saved validated parquet to %s", validated_path_local)

# Transform: extract fields
# country_name from name.common
df_valid["country_name"] = df_valid.get("name.common")
# currency_name: try to extract first currency's name if available

def extract_currency_name(row):
    currencies = row.get("currencies")
    if isinstance(currencies, dict):
        for k, v in currencies.items():
            if isinstance(v, dict) and v.get("name"):
                return v.get("name")
    return None

# currencies column may be nested dicts stored as objects; ensure it's raw dicts
if "currencies" in df_valid.columns:
    df_valid["currency_name"] = df_valid.apply(extract_currency_name, axis=1)
else:
    df_valid["currency_name"] = None

out_cols = ["country_name", "region", "population", "currency_name"]
transformed = df_valid[out_cols].copy()

# Write curated parquet partitioned by region
if curated_path:
    if os.path.exists(curated_path):
        if os.path.isdir(curated_path):
            shutil.rmtree(curated_path)
        else:
            os.remove(curated_path)
    transformed.to_parquet(curated_path, engine="pyarrow", index=False)
    logger.info("Saved transformed parquet to %s", curated_path)
else:
    if os.path.exists(curated_dir):
        shutil.rmtree(curated_dir)
    transformed.to_parquet(curated_dir, engine="pyarrow", index=False, partition_cols=["region"]) 
    logger.info("Saved transformed parquet to %s partitioned by region", curated_dir)
