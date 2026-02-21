# AWS Glue PySpark API Ingestion

## Overview

Use AWS Glue PySpark to fetch data directly from REST Countries API and save to S3.

---

## How It Works

```
AWS Glue Job (PySpark)
  ↓
fetch_api_data() → Calls REST Countries API
  ↓
save_as_json_file() → Saves JSON to S3
  ↓
s3://bucket/raw/countries/countries_raw_YYYYMMDD_HHMMSS.json
```

---

## Step 1: Verify Script is Uploaded to S3

```bash
aws s3 ls s3://data-pipeline-country-population/scripts/ingest_data.py
```

Should show the file. If not, upload it:

```bash
aws s3 cp Ingestion/ingest_data.py s3://data-pipeline-country-population/scripts/ingest_data.py
```

---

## Step 2: Configure Glue Job in Console

### Go to Glue Job

1. **AWS Glue → Jobs → country-population-ingestion**
2. Click **Edit job**
3. Verify configuration:
   - **Name:** `country-population-ingestion`
   - **IAM Role:** `glue-validation-role`
   - **Language:** Python (not Python Shell)
   - **Script location:** `s3://data-pipeline-country-population/scripts/ingest_data.py`
   - **Glue version:** 3.0
   - **Worker type:** G.1X
   - **Number of workers:** 3

### Add Logging Parameters

In **Script** tab at bottom, add **Job parameters**:

```
--enable-continuous-cloudwatch-log
true

--continuous-log-logGroup
/aws-glue/jobs/country-population-ingestion

--continuous-log-logStreamPrefix
ingestion
```

### Save the Job

Click **Save** button (critical!)

---

## Step 3: Verify Glue Role Has Required Permissions

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Check if role has S3 and CloudWatch permissions
aws iam get-role-policy \
  --role-name glue-validation-role \
  --policy-name S3AccessPolicy_datapipeline
```

If missing, add permissions:

```bash
aws iam put-role-policy \
  --role-name glue-validation-role \
  --policy-name GlueAndS3Access \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ],
        "Resource": [
          "arn:aws:s3:::data-pipeline-country-population/*",
          "arn:aws:s3:::data-pipeline-country-population"
        ]
      },
      {
        "Effect": "Allow",
        "Action": [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        "Resource": "arn:aws:logs:us-east-1:*:*"
      }
    ]
  }'
```

---

## Step 4: Create CloudWatch Log Group

```bash
aws logs create-log-group \
  --log-group-name /aws-glue/jobs/country-population-ingestion \
  --region us-east-1
```

---

## Step 5: Run the Job

```bash
# Start job
RUN_ID=$(aws glue start-job-run \
  --job-name country-population-ingestion \
  --region us-east-1 \
  --query 'JobRunId' \
  --output text)

echo "Job Run ID: $RUN_ID"

# Wait 30 seconds for logs to appear
sleep 30
```

---

## Step 6: Check Logs in CloudWatch

```bash
# View log streams
aws logs describe-log-streams \
  --log-group-name /aws-glue/jobs/country-population-ingestion \
  --region us-east-1 \
  --order-by LastEventTime \
  --descending \
  --query 'logStreams[0].logStreamName'
```

Get stream name, then view logs:

```bash
aws logs get-log-events \
  --log-group-name /aws-glue/jobs/country-population-ingestion \
  --log-stream-name ingestion-2024-02-22-00-10-00-xyz \
  --region us-east-1 \
  --query 'events[].message' \
  --output text
```

---

## Step 7: Verify Data in S3

```bash
# List files in raw zone
aws s3 ls s3://data-pipeline-country-population/raw/countries/

# View file
aws s3 cp s3://data-pipeline-country-population/raw/countries/countries_raw_20240222_001047.json - | head -20
```

---

## Complete Verification Script

```bash
#!/bin/bash

echo "=== Glue Ingestion Job Verification ==="

# Check script exists
echo "1. Checking script in S3..."
aws s3 ls s3://data-pipeline-country-population/scripts/ingest_data.py && echo "✓ Script exists"

# Check log group exists
echo "2. Checking log group..."
aws logs describe-log-groups \
  --log-group-name-prefix "/aws-glue/jobs/country-population-ingestion" \
  --query 'logGroups[0].logGroupName' || echo "Log group not found"

# Check job configuration
echo "3. Checking job configuration..."
aws glue get-job \
  --job-name country-population-ingestion \
  --region us-east-1 \
  --query 'Job.DefaultArguments' \
  --output json

# Run job
echo "4. Running job..."
RUN_ID=$(aws glue start-job-run \
  --job-name country-population-ingestion \
  --region us-east-1 \
  --query 'JobRunId' \
  --output text)

echo "Job Run ID: $RUN_ID"
echo "Waiting 60 seconds for completion..."
sleep 60

# Check job status
echo "5. Checking job status..."
aws glue get-job-run \
  --job-name country-population-ingestion \
  --run-id $RUN_ID \
  --region us-east-1 \
  --query 'JobRun.JobRunState'

# Check logs
echo "6. Checking logs..."
aws logs describe-log-streams \
  --log-group-name /aws-glue/jobs/country-population-ingestion \
  --region us-east-1 \
  --order-by LastEventTime \
  --descending \
  --query 'logStreams[0].logStreamName'

# Check S3 output
echo "7. Checking S3 output..."
aws s3 ls s3://data-pipeline-country-population/raw/countries/

echo "=== Verification Complete ==="
```

---

## Key Points

✅ **Uses native Glue PySpark** - No external scripts  
✅ **Fetches from API** - Uses requests library  
✅ **Saves as JSON** - Single file with timestamp  
✅ **Logs to CloudWatch** - Full visibility  
✅ **S3 permissions** - Glue role needs S3 access  

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No logs | Check log group exists and parameters saved |
| No S3 files | Check Glue role has S3 permissions |
| Job fails | Check CloudWatch logs for error details |
| API timeout | Increase worker count or timeout settings |

Done! ✅
