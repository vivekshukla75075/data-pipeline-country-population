# AWS Glue CloudWatch Logs Configuration

## Overview

Configure CloudWatch log groups for Glue jobs to view execution logs.

---

## Step 1: Create CloudWatch Log Groups

### Using AWS CLI

```bash
# Create log groups for all three jobs
aws logs create-log-group \
  --log-group-name /aws-glue/jobs/country-population-ingestion \
  --region us-east-1

aws logs create-log-group \
  --log-group-name /aws-glue/jobs/country-population-validation \
  --region us-east-1

aws logs create-log-group \
  --log-group-name /aws-glue/jobs/country-population-transformation \
  --region us-east-1
```

### Using AWS Console

1. Go to **CloudWatch → Logs → Log Groups**
2. Click **Create log group**
3. Enter name: `/aws-glue/jobs/country-population-ingestion`
4. Click **Create**
5. Repeat for validation and transformation jobs

---

## Step 2: Configure Glue Jobs with Logging

### For Ingestion Job

**Via AWS Console:**

1. Go to **Glue → Jobs → country-population-ingestion**
2. Click **Edit job**
3. Expand **Job details**
4. Scroll down to **Default job parameters**
5. Add these parameters:
   ```
   --enable-continuous-cloudwatch-log=true
   --continuous-log-logGroup=/aws-glue/jobs/country-population-ingestion
   --continuous-log-logStreamPrefix=ingestion
   ```
6. Click **Save job and edit script**

**Via AWS CLI:**

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws glue update-job \
  --name country-population-ingestion \
  --job-command Name=glueetl,ScriptLocation=s3://data-pipeline-country-population/scripts/ingest_data.py \
  --role arn:aws:iam::$ACCOUNT_ID:role/glue-validation-role \
  --glue-version "3.0" \
  --worker-type G.1X \
  --number-of-workers 3 \
  --default-arguments '{
    "--enable-continuous-cloudwatch-log": "true",
    "--continuous-log-logGroup": "/aws-glue/jobs/country-population-ingestion",
    "--continuous-log-logStreamPrefix": "ingestion",
    "--job-bookmark-option": "job-bookmark-enable"
  }' \
  --region us-east-1
```

### For Validation Job

**Via AWS Console:**

1. Go to **Glue → Jobs → country-population-validation**
2. Click **Edit job**
3. Add to **Default job parameters**:
   ```
   --enable-continuous-cloudwatch-log=true
   --continuous-log-logGroup=/aws-glue/jobs/country-population-validation
   --continuous-log-logStreamPrefix=validation
   ```
4. Click **Save job and edit script**

**Via AWS CLI:**

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws glue update-job \
  --name country-population-validation \
  --job-command Name=glueetl,ScriptLocation=s3://data-pipeline-country-population/scripts/validate_schema.py \
  --role arn:aws:iam::$ACCOUNT_ID:role/glue-validation-role \
  --glue-version "3.0" \
  --worker-type G.1X \
  --number-of-workers 3 \
  --default-arguments '{
    "--enable-continuous-cloudwatch-log": "true",
    "--continuous-log-logGroup": "/aws-glue/jobs/country-population-validation",
    "--continuous-log-logStreamPrefix": "validation",
    "--job-bookmark-option": "job-bookmark-enable"
  }' \
  --region us-east-1
```

### For Transformation Job

**Via AWS Console:**

1. Go to **Glue → Jobs → country-population-transformation**
2. Click **Edit job**
3. Add to **Default job parameters**:
   ```
   --enable-continuous-cloudwatch-log=true
   --continuous-log-logGroup=/aws-glue/jobs/country-population-transformation
   --continuous-log-logStreamPrefix=transformation
   ```
4. Click **Save job and edit script**

**Via AWS CLI:**

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws glue update-job \
  --name country-population-transformation \
  --job-command Name=glueetl,ScriptLocation=s3://data-pipeline-country-population/scripts/transform_data.py \
  --role arn:aws:iam::$ACCOUNT_ID:role/glue-validation-role \
  --glue-version "3.0" \
  --worker-type G.1X \
  --number-of-workers 5 \
  --default-arguments '{
    "--enable-continuous-cloudwatch-log": "true",
    "--continuous-log-logGroup": "/aws-glue/jobs/country-population-transformation",
    "--continuous-log-logStreamPrefix": "transformation",
    "--job-bookmark-option": "job-bookmark-enable"
  }' \
  --region us-east-1
```

---

## Step 3: View Logs

### In CloudWatch Console

1. Go to **CloudWatch → Logs → Log Groups**
2. Click `/aws-glue/jobs/country-population-ingestion`
3. Click on log stream (appears after job runs)
4. View log events

### Via AWS CLI

**List log streams:**

```bash
aws logs describe-log-streams \
  --log-group-name /aws-glue/jobs/country-population-ingestion \
  --region us-east-1
```

**View log events:**

```bash
aws logs get-log-events \
  --log-group-name /aws-glue/jobs/country-population-ingestion \
  --log-stream-name [STREAM_NAME] \
  --region us-east-1
```

---

## Step 4: Run Glue Job and Check Logs

**Run job:**

```bash
aws glue start-job-run \
  --job-name country-population-ingestion \
  --region us-east-1
```

**Wait for logs to appear (30 seconds after job starts)**

```bash
# Check log groups exist
aws logs describe-log-groups \
  --log-group-name-prefix "/aws-glue/jobs/" \
  --region us-east-1 \
  --query 'logGroups[].logGroupName' \
  --output text
```

---

## Quick Setup Commands

All three jobs in one go:

```bash
# Get Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/glue-validation-role"

# Create log groups
for job in ingestion validation transformation; do
  aws logs create-log-group \
    --log-group-name /aws-glue/jobs/country-population-$job \
    --region us-east-1 2>/dev/null || echo "Log group exists"
done

# Update jobs with logging
for job in ingestion validation transformation; do
  case $job in
    ingestion)
      SCRIPT="ingest_data.py"
      WORKERS=3
      ;;
    validation)
      SCRIPT="validate_schema.py"
      WORKERS=3
      ;;
    transformation)
      SCRIPT="transform_data.py"
      WORKERS=5
      ;;
  esac
  
  aws glue update-job \
    --name country-population-$job \
    --job-command Name=glueetl,ScriptLocation=s3://data-pipeline-country-population/scripts/$SCRIPT \
    --role $ROLE_ARN \
    --glue-version "3.0" \
    --worker-type G.1X \
    --number-of-workers $WORKERS \
    --default-arguments '{
      "--enable-continuous-cloudwatch-log": "true",
      "--continuous-log-logGroup": "/aws-glue/jobs/country-population-'$job'",
      "--continuous-log-logStreamPrefix": "'$job'",
      "--job-bookmark-option": "job-bookmark-enable"
    }' \
    --region us-east-1 2>/dev/null || echo "Job update failed"
done

echo "✅ All jobs configured with logging"
```

---

## Troubleshooting

### Logs Not Appearing

1. **Wait 30-60 seconds** after job starts
2. **Check job status**: `aws glue get-job-run --job-name [JOB_NAME] --run-id [RUN_ID]`
3. **Verify log group exists**: `aws logs describe-log-groups --log-group-name-prefix "/aws-glue/jobs/"`
4. **Check Glue job has logging parameters**: `aws glue get-job --name country-population-ingestion`

### Log Group Doesn't Exist

```bash
# Create missing log group
aws logs create-log-group --log-group-name /aws-glue/jobs/country-population-ingestion
```

### Job Fails Before Logs Appear

- Check Glue job parameters are correct
- Verify S3 paths in job configuration
- Check IAM role has S3 permissions

---

## Done! ✅

Your Glue jobs now have CloudWatch logging enabled. Logs will appear in `/aws-glue/jobs/[JOB_NAME]` when jobs run.
