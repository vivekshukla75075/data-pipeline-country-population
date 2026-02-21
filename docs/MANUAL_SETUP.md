# Manual AWS Setup Guide

Since your IAM user has limited permissions, follow these manual steps to set up the pipeline in AWS Console.

## Prerequisites

- AWS Console access
- S3 bucket: `data-pipeline-country-population` ✓ (Already created)
- Scripts uploaded to S3 ✓ (Already done)

## Step 1: Create Glue Jobs Manually

### Job 1: Ingestion

1. Go to **AWS Glue → Jobs → Create job**
2. Configure:
   - **Name:** `country-population-ingestion`
   - **IAM Role:** `glue-validation-role`
   - **Language:** Python (Spark)
   - **Script location:** `s3://data-pipeline-country-population/scripts/ingest_data.py`
   - **Worker type:** G.1X
   - **Number of workers:** 3
3. Click **Create job**

### Job 2: Validation

1. Click **Create job** again
2. Configure:
   - **Name:** `country-population-validation`
   - **IAM Role:** `glue-validation-role`
   - **Script location:** `s3://data-pipeline-country-population/scripts/validate_schema.py`
   - **Job parameters:**
     ```
     --bucket-name=data-pipeline-country-population
     --raw-path=raw/countries/countries_raw.json
     --validated-path=validated/countries/
     ```
3. Click **Create job**

### Job 3: Transformation

1. Click **Create job** again
2. Configure:
   - **Name:** `country-population-transformation`
   - **IAM Role:** `glue-validation-role`
   - **Script location:** `s3://data-pipeline-country-population/scripts/transform_data.py`
   - **Job parameters:**
     ```
     --bucket-name=data-pipeline-country-population
     --validated-path=validated/countries/
     --curated-path=curated/countries/
     ```
3. Click **Create job**

## Step 2: Test Glue Jobs

### Run Ingestion Job

1. Go to **Glue → Jobs → country-population-ingestion**
2. Click **Run job**
3. Wait for completion (check logs in CloudWatch)

### Run Validation Job

1. Go to **Glue → Jobs → country-population-validation**
2. Click **Run job**
3. Wait for completion

### Run Transformation Job

1. Go to **Glue → Jobs → country-population-transformation**
2. Click **Run job**
3. Wait for completion

## Step 3: Query Results in Athena

### Create External Table

1. Go to **Athena → Query Editor**
2. Run this query:

```sql
CREATE EXTERNAL TABLE IF NOT EXISTS country_population.countries_curated (
  country_name STRING,
  subregion STRING,
  population BIGINT,
  area DOUBLE,
  capital_city STRING,
  currency STRING
)
PARTITIONED BY (region STRING)
STORED AS PARQUET
LOCATION 's3://data-pipeline-country-population/curated/countries/'
TBLPROPERTIES ('classification'='parquet');
```

### Run Analytics

```sql
SELECT region, SUM(population) AS total_population, COUNT(*) AS country_count
FROM country_population.countries_curated
GROUP BY region
ORDER BY total_population DESC;
```

## Step 4: Upload Sample Data

If you don't have real data, upload sample:

```bash
cat > /tmp/sample.json <<'EOF'
[
  {"name":{"common":"USA"},"region":"Americas","population":331900000,"area":9833517,"capital":["Washington"]},
  {"name":{"common":"India"},"region":"Asia","population":1380004385,"area":3287263,"capital":["Delhi"]},
  {"name":{"common":"UK"},"region":"Europe","population":67736802,"area":242495,"capital":["London"]}
]
EOF

aws s3 cp /tmp/sample.json s3://data-pipeline-country-population/raw/countries/countries_raw.json
```

## Troubleshooting

### Job Failed

1. Go to **Glue → Jobs → [Job Name]**
2. Click **Runs** tab
3. Click run ID to view logs
4. Check CloudWatch Logs for errors

### No data in output

1. Verify raw data exists: `aws s3 ls s3://data-pipeline-country-population/raw/`
2. Check Glue job logs for errors
3. Run validation job manually to test

### Athena query returns no results

1. Verify transformation job completed
2. Check if parquet files exist: `aws s3 ls s3://data-pipeline-country-population/curated/`
3. Check partition location in S3

## What's Next?

Once data flows through the pipeline:

1. **Create QuickSight Dashboards:** Visualize population data by region
2. **Schedule Jobs:** Use EventBridge to run jobs on a schedule
3. **Add Monitoring:** Set up CloudWatch alarms for job failures
4. **Automate with Step Functions:** (Requires admin to create)

## Cost Estimation

- **Glue:** ~$0.44/DPU-hour (3 jobs × 2 hours/month) ≈ $2.64/month
- **S3:** ~$0.023/GB stored (sample data) ≈ $0.10/month
- **Athena:** ~$6.25/TB scanned (small queries) ≈ $0.01/month
- **Total:** ~$3-5/month with sample data
