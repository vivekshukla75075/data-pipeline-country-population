"""Validation: validate raw country JSON and produce validated parquet.

Description:
- Loads raw JSON (S3 or local) and validates rows (population present and > 0)
- Writes validated parquet output (overwrites existing validated output)

Logs info and errors using the standard Python `logging` module.
"""

import argparse
import os
import shutil
import logging

def run_local():
	import json
	import pandas as pd

	logger = logging.getLogger(__name__)

	root = os.path.dirname(os.path.dirname(__file__))

	raw_file = os.environ.get("RAW_FILE") or os.path.join(root, "output", "countries_raw.json")
	validated_dir = os.environ.get("VALIDATED_DIR") or os.path.join(root, "output", "validated", "countries")
	validated_path_env = os.environ.get("VALIDATED_PATH")
	os.makedirs(validated_dir, exist_ok=True)

	try:
		with open(raw_file, "r", encoding="utf-8") as f:
			data = json.load(f)
	except Exception:
		logger.exception("Failed to read raw file %s", raw_file)
		raise

	df = pd.json_normalize(data)
	df_valid = df[df["population"].notna() & (df["population"] > 0)].copy()

	if validated_path_env:
		validated_path = validated_path_env
	else:
		validated_path = os.path.join(validated_dir, "validated.parquet")

	# Overwrite: remove existing validated output (file or directory) before writing
	try:
		if os.path.exists(validated_path):
			if os.path.isdir(validated_path):
				shutil.rmtree(validated_path)
			else:
				os.remove(validated_path)

		df_valid.to_parquet(validated_path, engine="pyarrow", index=False)
		logger.info("Saved validated parquet to %s", validated_path)
	except Exception:
		logger.exception("Failed to write validated parquet to %s", validated_path)
		raise


def run_spark():
	import sys
	from pyspark.sql import SparkSession
	from pyspark.sql.functions import col

	spark = SparkSession.builder.appName("ValidationJob").getOrCreate()
	raw_df = spark.read.json("s3://my-bucket/raw/countries/countries_raw.json")
	validated_df = raw_df.filter(col("population").isNotNull() & (col("population") > 0))
	validated_df.write.mode("overwrite").parquet("s3://my-bucket/validated/countries/")


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("--local", action="store_true", help="Run validation using local files in output/")
	args = parser.parse_args()

	if args.local:
		run_local()
	else:
		run_spark()


if __name__ == "__main__":
	main()