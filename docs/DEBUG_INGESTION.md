# Debug Ingestion Job

## Problem: Ingestion Job Not Pulling Data from API

## Quick Checklist

- [ ] Script uploaded to S3: `s3://bucket/scripts/ingest_data.py`
- [ ] Job parameters have logging enabled
- [ ] CloudWatch log group exists: `/aws-glue/jobs/country-population-ingestion`
- [ ] Glue role has S3 permissions
- [ ] API is accessible: `https://restcountries.com/v3.1/all`

## Step 1: Upload Updated Script

```bash
# Upload the simplified ingestion script
aws s3 cp Ingestion/ingest_data.py s3://data-pipeline-country-population/scripts/ingest_data.py

echo "✓ Script uploaded"
```

## Step 2: Verify Job Configuration

```bash
# Check job script location
aws glue get-job \
  --job-name country-population-ingestion \
  --region us-east-1 \
  --query 'Job.Command.ScriptLocation'

# Should show: s3://data-pipeline-country-population/scripts/ingest_data.py
```

## Step 3: Create Log Group

```bash
aws logs create-log-group \
  --log-group-name /aws-glue/jobs/country-population-ingestion \
  --region us-east-1 2>/dev/null

echo "✓ Log group ready"
```

## Step 4: Add Logging to Job (CRITICAL)

Go to **AWS Glue Console**:

1. **Jobs → country-population-ingestion → Edit job**
2. Go to **Script** tab (Not Job details!)
3. Scroll to bottom - look for **Job parameters** section
4. Click **Add parameter** and add EACH one:
   - Key: `--enable-continuous-cloudwatch-log` | Value: `true`
   - Key: `--continuous-log-logGroup` | Value: `/aws-glue/jobs/country-population-ingestion`
   - Key: `--continuous-log-logStreamPrefix` | Value: `ingestion`
5. Click **Save** (important!)

## Step 5: Run Job and Check Logs

```bash
# Start job
RUN_ID=$(aws glue start-job-run \
  --job-name country-population-ingestion \
  --region us-east-1 \
  --query 'JobRunId' \
  --output text)

echo "Job Run ID: $RUN_ID"

# Wait 30 seconds
sleep 30

# Get log stream name
STREAM=$(aws logs describe-log-streams \
  --log-group-name /aws-glue/jobs/country-population-ingestion \
  --region us-east-1 \
  --order-by LastEventTime \
  --descending \
  --query 'logStreams[0].logStreamName' \
  --output text 2>/dev/null)

echo "Log Stream: $STREAM"

# View logs
if [ -n "$STREAM" ] && [ "$STREAM" != "None" ]; then
	aws logs get-log-events \
	  --log-group-name /aws-glue/jobs/country-population-ingestion \
	  --log-stream-name $STREAM \
	  --region us-east-1 \
	  --query 'events[].message' \
	  --output text
else
	echo "No logs found - logging may not be configured"
fi
```

## Step 6: Check S3 for Output

```bash
# List raw bucket
aws s3 ls s3://data-pipeline-country-population/raw/countries/

# Should show: countries_raw_YYYYMMDD_HHMMSS.json
```

## If Still No Data in S3

### Test 1: Verify API is Accessible

```bash
curl -I https://restcountries.com/v3.1/all

# Should return 200 OK
```

### Test 2: Check Job Status

```bash
aws glue get-job-run \
  --job-name country-population-ingestion \
  --run-id $RUN_ID \
  --region us-east-1
```

Look for `JobRunState`:
- `SUCCEEDED` - Job ran but didn't create files (check logs)
- `FAILED` - Job failed (check logs for error)
- `TIMEOUT` - Job took too long

### Test 3: Check Glue Role Permissions

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Check S3 permissions
aws iam get-role-policy \
  --role-name glue-validation-role \
  --policy-name S3AccessPolicy_datapipeline
```

If missing, add permissions:

```bash
aws iam put-role-policy \
  --role-name glue-validation-role \
  --policy-name S3FullAccess \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["s3:*"],
      "Resource": ["arn:aws:s3:::data-pipeline-country-population/*"]
    }]
  }'
```

### Test 4: View Full Error in Logs

If logs show errors, look for:
- `✗ API fetch failed` - API unreachable or timeout
- `✗ S3 upload failed` - Permission or S3 issue
- `Fatal error` - Script initialization error

## Complete Debug Script

```bash
#!/bin/bash

echo "=== Ingestion Debug ==="

echo "1. Uploading script..."
aws s3 cp Ingestion/ingest_data.py s3://data-pipeline-country-population/scripts/ingest_data.py

echo "2. Creating log group..."
aws logs create-log-group --log-group-name /aws-glue/jobs/country-population-ingestion --region us-east-1 2>/dev/null

echo "3. Checking job configuration..."
aws glue get-job --job-name country-population-ingestion --region us-east-1 --query 'Job.Command.ScriptLocation'

echo "4. Running job..."
RUN_ID=$(aws glue start-job-run --job-name country-population-ingestion --region us-east-1 --query 'JobRunId' --output text)
echo "Run ID: $RUN_ID"

echo "5. Waiting 60 seconds..."
sleep 60

echo "6. Checking job status..."
aws glue get-job-run --job-name country-population-ingestion --run-id $RUN_ID --region us-east-1 --query 'JobRun.JobRunState'

echo "7. Checking logs..."
STREAM=$(aws logs describe-log-streams --log-group-name /aws-glue/jobs/country-population-ingestion --region us-east-1 --order-by LastEventTime --descending --query 'logStreams[0].logStreamName' --output text 2>/dev/null)
if [ -n "$STREAM" ] && [ "$STREAM" != "None" ]; then
	aws logs get-log-events --log-group-name /aws-glue/jobs/country-population-ingestion --log-stream-name $STREAM --region us-east-1 --query 'events[].message' --output text
fi

echo "8. Checking S3 output..."
aws s3 ls s3://data-pipeline-country-population/raw/countries/

echo "=== End Debug ==="
```

Save and run:
```bash
chmod +x debug_ingestion.sh
./debug_ingestion.sh
```

Done! ✅
