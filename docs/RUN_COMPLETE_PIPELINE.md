# Complete End-to-End Pipeline Execution

## Overview

The ETL pipeline has 3 stages that must run in order:
1. **Ingestion** → Fetch API data → Upload to `raw/countries/`
2. **Validation** → Read raw → Filter → Upload to `validated/countries/` → Archive raw
3. **Transformation** → Read validated → Transform → Upload to `curated/countries/`

---

## Step 1: Run Ingestion Job First

**IMPORTANT: Ingestion must run FIRST to pull data from API**

```bash
aws glue start-job-run \
  --job-name country-population-ingestion \
  --region us-east-1
```

Get the Job Run ID from the response.

### Verify Ingestion Succeeded

```bash
# Wait 30 seconds, then check status
aws glue get-job-run \
  --job-name country-population-ingestion \
  --run-id <RUN_ID_FROM_ABOVE> \
  --region us-east-1 \
  --query 'JobRun.JobRunState'
```

Should show: `SUCCEEDED`

### Verify Data in S3

```bash
# List files uploaded by ingestion job
aws s3 ls s3://data-pipeline-country-population/raw/countries/
```

Should show files like: `countries_raw_20240222_101530.json`

---

## Step 2: Run Validation Job

Only run AFTER ingestion has completed.

```bash
aws glue start-job-run \
  --job-name country-population-validation \
  --region us-east-1 \
  --arguments '{
    "--bucket-name": "data-pipeline-country-population",
    "--raw-path": "raw/countries/",
    "--validated-path": "validated/countries/"
  }'
```

### Verify Validation Succeeded

```bash
# Check status
aws glue get-job-run \
  --job-name country-population-validation \
  --run-id <RUN_ID> \
  --region us-east-1 \
  --query 'JobRun.JobRunState'
```

### Verify Output in S3

```bash
# Check validated data
aws s3 ls s3://data-pipeline-country-population/validated/countries/

# Check raw archive (processed files moved here)
aws s3 ls s3://data-pipeline-country-population/raw/countries_archive/
```

---

## Step 3: Run Transformation Job

Only run AFTER validation has completed.

```bash
aws glue start-job-run \
  --job-name country-population-transformation \
  --region us-east-1 \
  --arguments '{
    "--bucket-name": "data-pipeline-country-population",
    "--validated-path": "validated/countries/",
    "--curated-path": "curated/countries/"
  }'
```

### Verify Transformation Succeeded

```bash
# Check status
aws glue get-job-run \
  --job-name country-population-transformation \
  --run-id <RUN_ID> \
  --region us-east-1 \
  --query 'JobRun.JobRunState'
```

### Verify Final Output

```bash
# Check curated data
aws s3 ls s3://data-pipeline-country-population/curated/countries/
```

Should show partitioned parquet files by region.

---

## Complete Pipeline Flow (All 3 Jobs)

```bash
#!/bin/bash

echo "========== Starting ETL Pipeline =========="

# Job 1: Ingestion
echo "Step 1: Running Ingestion Job..."
INGEST_RUN=$(aws glue start-job-run \
  --job-name country-population-ingestion \
  --region us-east-1 \
  --query 'JobRunId' \
  --output text)

echo "Ingestion Job ID: $INGEST_RUN"
echo "Waiting for ingestion to complete..."
sleep 60

# Job 2: Validation
echo "Step 2: Running Validation Job..."
VALIDATE_RUN=$(aws glue start-job-run \
  --job-name country-population-validation \
  --region us-east-1 \
  --arguments '{
    "--bucket-name": "data-pipeline-country-population",
    "--raw-path": "raw/countries/",
    "--validated-path": "validated/countries/"
  }' \
  --query 'JobRunId' \
  --output text)

echo "Validation Job ID: $VALIDATE_RUN"
echo "Waiting for validation to complete..."
sleep 60

# Job 3: Transformation
echo "Step 3: Running Transformation Job..."
TRANSFORM_RUN=$(aws glue start-job-run \
  --job-name country-population-transformation \
  --region us-east-1 \
  --arguments '{
    "--bucket-name": "data-pipeline-country-population",
    "--validated-path": "validated/countries/",
    "--curated-path": "curated/countries/"
  }' \
  --query 'JobRunId' \
  --output text)

echo "Transformation Job ID: $TRANSFORM_RUN"
echo "Waiting for transformation to complete..."
sleep 60

# Verify all jobs succeeded
echo ""
echo "========== Verification =========="
echo "Checking Ingestion:"
aws glue get-job-run --job-name country-population-ingestion --run-id $INGEST_RUN --region us-east-1 --query 'JobRun.JobRunState'

echo "Checking Validation:"
aws glue get-job-run --job-name country-population-validation --run-id $VALIDATE_RUN --region us-east-1 --query 'JobRun.JobRunState'

echo "Checking Transformation:"
aws glue get-job-run --job-name country-population-transformation --run-id $TRANSFORM_RUN --region us-east-1 --query 'JobRun.JobRunState'

echo ""
echo "========== S3 Output =========="
echo "Raw Data:"
aws s3 ls s3://data-pipeline-country-population/raw/countries/

echo "Validated Data:"
aws s3 ls s3://data-pipeline-country-population/validated/countries/

echo "Curated Data:"
aws s3 ls s3://data-pipeline-country-population/curated/countries/ --recursive

echo ""
echo "✅ Pipeline Complete!"
```

---

## Troubleshooting

### No Data in Raw Folder

1. **Check ingestion job parameters are saved:**
   ```bash
   aws glue get-job --job-name country-population-ingestion --region us-east-1 --query 'Job.DefaultArguments'
   ```

2. **Check ingestion job logs:**
   ```bash
   aws logs describe-log-streams \
     --log-group-name /aws-glue/jobs/country-population-ingestion \
     --region us-east-1
   ```

3. **Verify API is accessible:**
   ```bash
   curl -I https://restcountries.com/v3.1/all
   ```

### Validation Job Doesn't Process Data

- Ensure ingestion ran first and data exists in `raw/countries/`
- Check validation job has correct `--raw-path` parameter

### No Output in Validated or Curated

- Check previous job succeeded
- Verify S3 paths in job parameters are correct

---

## Summary

✅ **Run Ingestion first** (pulls API data)  
✅ **Run Validation second** (processes raw data)  
✅ **Run Transformation third** (creates final output)  
✅ **Check S3 output** at each stage  

Done! ✅
