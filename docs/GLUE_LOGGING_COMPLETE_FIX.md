# Complete Fix: Glue Job CloudWatch Logging Not Working

## Issue

Parameters are set but logs still not appearing in CloudWatch.

## Root Cause

The job needs to be **SAVED** after editing parameters. Simply viewing the parameters isn't enough.

---

## Complete Fix - Step by Step

### Step 1: Go to Job Configuration

1. Go to **AWS Glue → Jobs → country-population-ingestion**
2. Click **Edit job** button (top right)

### Step 2: Verify Parameters Are Set

Look for **Default job parameters** section. You should already see:
```
--enable-continuous-cloudwatch-log=true
--continuous-log-logGroup=/aws-glue/jobs/country-population-ingestion
--continuous-log-logStreamPrefix=ingestion
```

### Step 3: SAVE THE JOB (CRITICAL STEP)

⚠️ **This is the most important step:**

1. Scroll to the **very bottom** of the page
2. Click the **"Save job and edit script"** button (NOT just "Save")
3. Wait for the page to show "Job saved successfully" message
4. The page will reload

### Step 4: Verify Job is Saved

1. Go back to **Jobs → country-population-ingestion**
2. Click **Edit job** again
3. Scroll to **Job details** section
4. Verify the parameters are STILL there
5. If they're gone, go back to Step 2 and repeat

### Step 5: Run the Job

```bash
aws glue start-job-run \
  --job-name country-population-ingestion \
  --region us-east-1
```

You'll get a `JobRunId` in response. Copy this ID.

### Step 6: Wait and Check Logs

**Wait 30-60 seconds** for logs to start appearing.

Then check:

```bash
# Check for log streams
aws logs describe-log-streams \
  --log-group-name /aws-glue/jobs/country-population-ingestion \
  --region us-east-1 \
  --order-by LastEventTime \
  --descending
```

You should see log streams like:
```
ingestion-2024-01-15-10-30-45-abc123
```

### Step 7: View Log Events

```bash
# Replace STREAM_NAME with actual stream name from Step 6
aws logs get-log-events \
  --log-group-name /aws-glue/jobs/country-population-ingestion \
  --log-stream-name ingestion-2024-01-15-10-30-45-abc123 \
  --region us-east-1
```

You should now see the actual log events!

---

## Checklist - Must Do All

- [ ] Go to job edit page
- [ ] Verify parameters are shown
- [ ] Click **"Save job and edit script"** button
- [ ] Wait for "Job saved successfully" message
- [ ] Go back to job and re-verify parameters are still there
- [ ] Run the job with `aws glue start-job-run`
- [ ] Wait 30-60 seconds
- [ ] Check CloudWatch log streams
- [ ] View log events

---

## If Still No Logs After All Steps

### Check 1: Verify Log Group Exists

```bash
aws logs describe-log-groups \
  --log-group-name-prefix "/aws-glue/jobs/" \
  --region us-east-1
```

Should show:
```
/aws-glue/jobs/country-population-ingestion
```

If missing, create it:
```bash
aws logs create-log-group \
  --log-group-name /aws-glue/jobs/country-population-ingestion \
  --region us-east-1
```

### Check 2: Verify Job Parameters Actually Saved

```bash
aws glue get-job \
  --name country-population-ingestion \
  --region us-east-1 \
  --query 'Job.DefaultArguments'
```

Should show:
```json
{
  "--continuous-log-logGroup": "/aws-glue/jobs/country-population-ingestion",
  "--continuous-log-logStreamPrefix": "ingestion",
  "--enable-continuous-cloudwatch-log": "true"
}
```

If these aren't shown, the save didn't work. Go back to Step 2-3.

### Check 3: Check Job Status

```bash
# Replace RUN_ID with actual run ID from Step 5
aws glue get-job-run \
  --job-name country-population-ingestion \
  --run-id <RUN_ID> \
  --region us-east-1
```

Check the `JobRunState`:
- `RUNNING` - Wait longer for logs
- `SUCCEEDED` - Job completed, logs should exist
- `FAILED` - Check error logs for why job failed

### Check 4: IAM Role Permissions

The `glue-validation-role` needs CloudWatch Logs permissions. Run:

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws iam put-role-policy \
  --role-name glue-validation-role \
  --policy-name AllowCloudWatchLogs \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        "Resource": "arn:aws:logs:us-east-1:'$ACCOUNT_ID':*"
      }
    ]
  }'
```

---

## Final Steps

After completing ALL checks above:

1. **Save the job again**
2. **Run a new job run**
3. **Wait 60 seconds**
4. **Check CloudWatch**

Your logs should now appear! ✅

---

## Key Takeaways

🔑 **MUST click "Save job and edit script"** - not just "Save"  
🔑 **Verify parameters persist** after save  
🔑 **Wait at least 30 seconds** for logs to appear  
🔑 **Job must complete** to show logs  
🔑 **IAM role needs CloudWatch permissions**
