"""Transformation: read validated data and produce curated parquet.

Description:
- Reads validated parquet (S3 or local), flattens fields, and writes curated parquet
- Local mode uses pandas/pyarrow and writes partitioned parquet into `output/curated/`

Logs info and errors using the standard Python `logging` module.
"""

import argparse
import os
import shutil
import logging


def run_local():
    import pandas as pd
    logger = logging.getLogger(__name__)

    root = os.path.dirname(os.path.dirname(__file__))
    validated_path = os.environ.get("VALIDATED_PATH") or os.path.join(root, "output", "validated", "countries", "validated.parquet")
    curated_dir = os.environ.get("CURATED_DIR") or os.path.join(root, "output", "curated", "countries")
    curated_path_env = os.environ.get("CURATED_PATH")
    os.makedirs(curated_dir, exist_ok=True)

    try:
        df = pd.read_parquet(validated_path, engine="pyarrow")
    except Exception:
        logger.exception("Failed to read validated parquet from %s", validated_path)
        raise

    # country_name from name.common
    if "name.common" in df.columns:
        df["country_name"] = df["name.common"]
    else:
        df["country_name"] = None

    def extract_currency_name(x):
        if not x or not isinstance(x, dict):
            return None
        for k, v in x.items():
            if isinstance(v, dict) and v.get("name"):
                return v.get("name")
        return None

    if "currencies" in df.columns:
        df["currency_name"] = df["currencies"].apply(extract_currency_name)
    else:
        df["currency_name"] = None

    out_cols = ["country_name", "region", "population", "currency_name"]
    transformed = df[out_cols].copy()

    # Overwrite: remove existing curated output before writing
    try:
        if curated_path_env:
            if os.path.exists(curated_path_env):
                if os.path.isdir(curated_path_env):
                    shutil.rmtree(curated_path_env)
                else:
                    os.remove(curated_path_env)
            transformed.to_parquet(curated_path_env, engine="pyarrow", index=False)
            logger.info("Saved transformed parquet to %s", curated_path_env)
        else:
            if os.path.exists(curated_dir):
                shutil.rmtree(curated_dir)
            transformed.to_parquet(curated_dir, engine="pyarrow", index=False, partition_cols=["region"]) 
            logger.info("Saved transformed parquet to %s partitioned by region", curated_dir)
    except Exception:
        logger.exception("Failed to write transformed parquet")
        raise


def run_spark():
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import col

    spark = SparkSession.builder.appName("TransformationJob").getOrCreate()
    validated_df = spark.read.parquet("s3://my-bucket/validated/countries/")
    transformed_df = validated_df.select(
        col("name.common").alias("country_name"),
        col("region"),
        col("population"),
        col("currencies.USD.name").alias("currency_name")
    )
    transformed_df.write.mode("overwrite").partitionBy("region").parquet(
        "s3://my-bucket/curated/countries/"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--local", action="store_true", help="Run transformation locally using output/validated/")
    args = parser.parse_args()

    if args.local:
        run_local()
    else:
        run_spark()


if __name__ == "__main__":
    main()