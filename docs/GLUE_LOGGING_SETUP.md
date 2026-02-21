# AWS Glue Logging Configuration

## Problem

When running Glue jobs, you get error:
```
An error occurred while describing log streams.
The specified log group does not exist.
```

## Solution

### Step 1: Create CloudWatch Log Groups

```bash
aws logs create-log-group --log-group-name /aws-glue/jobs/country-population-ingestion --region us-east-1
aws logs create-log-group --log-group-name /aws-glue/jobs/country-population-validation --region us-east-1
aws logs create-log-group --log-group-name /aws-glue/jobs/country-population-transformation --region us-east-1
```

### Step 2: Configure Glue Jobs with Logging

Run the configuration script:

```bash
chmod +x infrastructure/scripts/configure_glue_logging.sh
./infrastructure/scripts/configure_glue_logging.sh
```

Or manually update each job in AWS Console:

1. Go to **Glue → Jobs → [Job Name]**
2. Click **Edit**
3. Expand **Job details**
4. Under **Default job parameters**, add:
   ```
   --enable-continuous-cloudwatch-log=true
   --continuous-log-logGroup=/aws-glue/jobs/[JOB_NAME]
   --continuous-log-logStreamPrefix=prefix
   ```
5. Click **Save job and edit script**

### Step 3: View Logs in CloudWatch

After running Glue job:

1. Go to **CloudWatch → Logs → Log Groups**
2. Select `/aws-glue/jobs/[JOB_NAME]`
3. View log streams and messages

Or via CLI:

```bash
# List log streams
aws logs describe-log-streams \
  --log-group-name /aws-glue/jobs/country-population-ingestion \
  --region us-east-1

# View log events
aws logs get-log-events \
  --log-group-name /aws-glue/jobs/country-population-ingestion \
  --log-stream-name [STREAM_NAME] \
  --region us-east-1
```

### Step 4: Run Glue Job

```bash
# Run ingestion job
aws glue start-job-run \
  --job-name country-population-ingestion \
  --region us-east-1

# Check job status
aws glue get-job-run \
  --job-name country-population-ingestion \
  --run-id [RUN_ID] \
  --region us-east-1
```

---

## Troubleshooting

### Still no logs showing

1. **Wait 30 seconds** - Logs may take time to appear
2. **Check job status** - Job must be SUCCEEDED or FAILED to have logs
3. **Verify log group exists:**
   ```bash
   aws logs describe-log-groups --log-group-name-prefix "/aws-glue/jobs/"
   ```
4. **Verify job has logging enabled:**
   ```bash
   aws glue get-job --name country-population-ingestion | grep -i "log"
   ```

### Log group deleted accidentally

Recreate:
```bash
aws logs create-log-group --log-group-name /aws-glue/jobs/country-population-ingestion
```

Done! ✅
