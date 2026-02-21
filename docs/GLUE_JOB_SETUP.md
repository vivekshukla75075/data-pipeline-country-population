# AWS Glue Job Setup Guide

## Creating Glue Jobs Correctly

### Step 1: Create CloudWatch Log Group (Optional but Recommended)

```bash
aws logs create-log-group --log-group-name /aws-glue/jobs/country-population-ingestion
aws logs create-log-group --log-group-name /aws-glue/jobs/country-population-validation
aws logs create-log-group --log-group-name /aws-glue/jobs/country-population-transformation
```

### Step 2: Create Ingestion Glue Job

1. Go to **AWS Glue → Jobs → Create job**
2. Configure:
   - **Name:** `country-population-ingestion`
   - **IAM Role:** `glue-validation-role`
   - **Language:** Python (Spark)
   - **Script location:** `s3://data-pipeline-country-population/scripts/ingest_data.py`
   - **Worker type:** G.1X
   - **Number of workers:** 3
   - **Max capacity:** 10 DPU

3. **Job parameters (optional):**
   ```
   --S3_BUCKET=data-pipeline-country-population
   --API_URL=https://restcountries.com/v3.1/all
   ```

4. Click **Create job**

### Step 3: Create Validation Glue Job

1. Click **Create job**
2. Configure:
   - **Name:** `country-population-validation`
   - **IAM Role:** `glue-validation-role`
   - **Script location:** `s3://data-pipeline-country-population/scripts/validate_schema.py`
   - **Worker type:** G.1X
   - **Number of workers:** 3

3. **Job parameters:**
   ```
   --bucket-name=data-pipeline-country-population
   --raw-path=raw/countries/
   --validated-path=validated/countries/
   ```

4. Click **Create job**

### Step 4: Create Transformation Glue Job

1. Click **Create job**
2. Configure:
   - **Name:** `country-population-transformation`
   - **IAM Role:** `glue-validation-role`
   - **Script location:** `s3://data-pipeline-country-population/scripts/transform_data.py`
   - **Worker type:** G.1X
   - **Number of workers:** 5

3. **Job parameters:**
   ```
   --bucket-name=data-pipeline-country-population
   --validated-path=validated/countries/
   --curated-path=curated/countries/
   ```

4. Click **Create job**

---

## Running Glue Jobs

### Via AWS Console

1. Go to **Glue → Jobs**
2. Select job name
3. Click **Run job**
4. Wait for completion and check logs

### Via AWS CLI

```bash
# Run ingestion job
aws glue start-job-run \
  --job-name country-population-ingestion \
  --region us-east-1

# Run validation job
aws glue start-job-run \
  --job-name country-population-validation \
  --region us-east-1

# Run transformation job
aws glue start-job-run \
  --job-name country-population-transformation \
  --region us-east-1
```

---

## Troubleshooting

### Log Group Does Not Exist Error

**Solution:** Create log groups before running jobs:

```bash
aws logs create-log-group --log-group-name /aws-glue/jobs/country-population-ingestion
```

### Job Fails with Access Denied

**Check:** IAM role `glue-validation-role` has:
- S3 full access to bucket
- CloudWatch Logs permissions
- Glue service permissions

### Job Runs but Produces No Output

**Check:**
1. Raw data exists in S3: `aws s3 ls s3://data-pipeline-country-population/raw/`
2. Job parameters are correct
3. Check CloudWatch logs for details

---

## Job Execution Order

1. **Ingestion Job** → Fetches API data → Uploads to `raw/countries/`
2. **Validation Job** → Reads raw data → Outputs to `validated/countries/` → Moves raw to archive
3. **Transformation Job** → Reads validated → Outputs to `curated/countries/`

Done! ✅
