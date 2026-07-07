# Setup Instructions - ETL Pipeline

## Prerequisites

Before running the pipeline, ensure the following are set up:

### 1. IAM Permissions (Admin Only)

The `data-pipeline-country-population` IAM user needs the following permissions:

#### Lambda Update Permissions
```json
{
  "Sid": "UpdateLambdaFunction",
  "Effect": "Allow",
  "Action": [
    "lambda:UpdateFunctionCode",
    "lambda:GetFunction",
    "lambda:GetFunctionConfiguration",
    "lambda:InvokeFunction"
  ],
  "Resource": "arn:aws:lambda:us-east-1:778277577996:function:ingest-api-data"
}
```

#### Glue Create/Delete Permissions
```json
{
  "Sid": "GlueJobManagement",
  "Effect": "Allow",
  "Action": [
    "glue:CreateJob",
    "glue:DeleteJob",
    "glue:GetJob",
    "glue:StartJobRun",
    "glue:GetJobRun"
  ],
  "Resource": "arn:aws:glue:us-east-1:778277577996:job/*"
}
```

#### S3 Access (Already configured)
```json
{
  "Sid": "S3Access",
  "Effect": "Allow",
  "Action": ["s3:*"],
  "Resource": ["arn:aws:s3:::data-pipeline-country-population/*"]
}
```

### 2. Setup Glue Jobs (Must be done once)

Run the setup script to create Glue jobs:

```bash
chmod +x infrastructure/scripts/setup_glue_jobs.sh
./infrastructure/scripts/setup_glue_jobs.sh
```

This will:
- ✅ Create country-population-validation job
- ✅ Create country-population-transformation job
- ✅ Configure with correct script locations
- ✅ Set proper worker types and counts

## Running the Pipeline

### Step 1: Trigger Lambda Ingestion

```bash
aws lambda invoke \
  --function-name ingest-api-data \
  --region us-east-1 \
  response.json

cat response.json | jq '.'
```

Wait 30 seconds for data to appear in S3.

### Step 2: Run Validation Job

```bash
aws glue start-job-run \
  --job-name country-population-validation \
  --region us-east-1

# Check status
aws glue get-job-run \
  --job-name country-population-validation \
  --run-id <JOB_RUN_ID> \
  --region us-east-1 \
  --query 'JobRun.JobRunState'
```

Wait 90 seconds for validation to complete.

### Step 3: Run Transformation Job

```bash
aws glue start-job-run \
  --job-name country-population-transformation \
  --region us-east-1

# Check status
aws glue get-job-run \
  --job-name country-population-transformation \
  --run-id <JOB_RUN_ID> \
  --region us-east-1 \
  --query 'JobRun.JobRunState'
```

Wait 90 seconds for transformation to complete.

## Verify Results

### Check S3 Data

```bash
# Raw data
aws s3 ls s3://data-pipeline-country-population/raw/countries/ --region us-east-1

# Validated data
aws s3 ls s3://data-pipeline-country-population/validated/countries/ --region us-east-1

# Curated data
aws s3 ls s3://data-pipeline-country-population/curated/countries/ --region us-east-1 --recursive
```

### Check Logs

```bash
# Ingestion logs
aws s3 ls s3://data-pipeline-country-population/logs/ingestion_logs/ --region us-east-1

# Validation logs
aws s3 ls s3://data-pipeline-country-population/logs/validation_logs/ --region us-east-1

# Transformation logs
aws s3 ls s3://data-pipeline-country-population/logs/transformation_logs/ --region us-east-1
```

## Troubleshooting

### Lambda function not found
- Ensure Lambda function `ingest-api-data` exists
- Check: `aws lambda get-function --function-name ingest-api-data --region us-east-1`

### Glue job metadata error
- Run the setup script: `./infrastructure/scripts/setup_glue_jobs.sh`
- Verify scripts are in S3: `aws s3 ls s3://data-pipeline-country-population/scripts/`

### Permission denied errors
- Ask admin to grant required IAM permissions (see Prerequisites above)
- Verify: `aws iam get-user-policy --user-name data-pipeline-country-population --policy-name <PolicyName>`

## GitHub Actions Deployment

The GitHub Actions workflow automatically:
1. ✅ Builds Lambda package
2. ✅ Creates/updates Lambda function
3. ✅ Uploads Glue scripts to S3
4. ⚠️ Requires admin to create Glue jobs (use setup script)

## Support

For issues:
1. Check logs in S3
2. Verify IAM permissions
3. Ensure scripts are uploaded to S3
4. Run setup script to recreate Glue jobs
