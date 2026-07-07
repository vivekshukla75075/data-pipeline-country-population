# Diagnose Ingestion Job Issues

## Problem

Ingestion job shows "Succeeded" but:
- No logs in CloudWatch
- No data in S3 raw bucket

## Root Causes

1. **Logging parameters not saved** in Glue job
2. **Script not executing** properly in Glue
3. **S3 permissions issue** - can't write to bucket
4. **API call failing silently**

---

## Step 1: Check Ingestion Job Configuration

```bash
# Verify job has logging parameters
aws glue get-job \
  --job-name country-population-ingestion \
  --region us-east-1 \
  --query 'Job.DefaultArguments' \
  --output json
```

**Must show:**
```json
{
  "--enable-continuous-cloudwatch-log": "true",
  "--continuous-log-logGroup": "/aws-glue/jobs/country-population-ingestion",
  "--continuous-log-logStreamPrefix": "ingestion"
}
```

If empty `{}`, **logging parameters weren't saved**. Go to:
1. **Glue → Jobs → country-population-ingestion**
2. Click **Edit job**
3. Go to **Script** tab
4. Look for **Job parameters** section at bottom
5. Add parameters if missing
6. Click **Save**

---

## Step 2: Verify Log Group Exists

```bash
aws logs describe-log-groups \
  --log-group-name-prefix "/aws-glue/jobs/" \
  --region us-east-1
```

If `/aws-glue/jobs/country-population-ingestion` is missing, create it:

```bash
aws logs create-log-group \
  --log-group-name /aws-glue/jobs/country-population-ingestion \
  --region us-east-1
```

---

## Step 3: Check S3 Bucket Permissions

Verify the Glue role has S3 permissions:

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws iam get-role-policy \
  --role-name glue-validation-role \
  --policy-name S3AccessPolicy_datapipeline \
  --region us-east-1
```

If policy is missing, add it:

```bash
aws iam put-role-policy \
  --role-name glue-validation-role \
  --policy-name S3FullAccess \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ],
        "Resource": [
          "arn:aws:s3:::data-pipeline-country-population/*",
          "arn:aws:s3:::data-pipeline-country-population"
        ]
      }
    ]
  }'
```

---

## Step 4: Run Ingestion and Check Logs

```bash
# Run job
RUN_ID=$(aws glue start-job-run \
  --job-name country-population-ingestion \
  --region us-east-1 \
  --query 'JobRunId' \
  --output text)

echo "Job Run ID: $RUN_ID"

# Wait 30 seconds
sleep 30

# Check for log streams
aws logs describe-log-streams \
  --log-group-name /aws-glue/jobs/country-population-ingestion \
  --region us-east-1 \
  --order-by LastEventTime \
  --descending
```

**If log streams appear**, view events:

```bash
# Replace STREAM_NAME with actual stream from above
aws logs get-log-events \
  --log-group-name /aws-glue/jobs/country-population-ingestion \
  --log-stream-name ingestion-2024-02-22-00-10-00-xyz \
  --region us-east-1
```

---

## Step 5: Check S3 for Data

```bash
# Check if data was uploaded
aws s3 ls s3://data-pipeline-country-population/raw/countries/
```

**Expected output:**
