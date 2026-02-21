# Fix: Glue Job CloudWatch Logging

## Problem

- Log groups exist in CloudWatch
- But Glue jobs don't write logs to them
- "Log stream not found" error when viewing logs

## Solution: Add Logging Parameters to Glue Jobs

### Step 1: Edit Ingestion Job

1. Go to **AWS Glue → Jobs → country-population-ingestion**
2. Click **Edit job**
3. Expand **Job details** section
4. Scroll down to find **Default job parameters** field
5. **Add ONLY these parameters** (exactly as shown):
   ```
   --enable-continuous-cloudwatch-log
   true
   --continuous-log-logGroup
   /aws-glue/jobs/country-population-ingestion
   --continuous-log-logStreamPrefix
   ingestion
   ```
   
   OR add as a single line:
   ```
   --enable-continuous-cloudwatch-log true --continuous-log-logGroup /aws-glue/jobs/country-population-ingestion --continuous-log-logStreamPrefix ingestion
   ```

6. Scroll down and click **Save job and edit script** button
7. Wait for job to save (you'll see "Job Saved" message)

### Step 2: Edit Validation Job

1. Go to **AWS Glue → Jobs → country-population-validation**
2. Click **Edit job**
3. Expand **Job details**
4. Add to **Default job parameters**:
   ```
   --enable-continuous-cloudwatch-log true --continuous-log-logGroup /aws-glue/jobs/country-population-validation --continuous-log-logStreamPrefix validation
   ```
5. Click **Save job and edit script**

### Step 3: Edit Transformation Job

1. Go to **AWS Glue → Jobs → country-population-transformation**
2. Click **Edit job**
3. Expand **Job details**
4. Add to **Default job parameters**:
   ```
   --enable-continuous-cloudwatch-log true --continuous-log-logGroup /aws-glue/jobs/country-population-transformation --continuous-log-logStreamPrefix transformation
   ```
5. Click **Save job and edit script**

---

## Step 4: Run Job and View Logs

### Run the Job

```bash
aws glue start-job-run --job-name country-population-ingestion --region us-east-1
```

### Wait 30 Seconds

Let the job start and begin logging.

### View Logs in Glue Console

1. Go to **Glue → Jobs → country-population-ingestion**
2. Click on the **Runs** tab
3. Click on the newest run
4. You should now see **Logs** tab with output/error logs

### View Logs in CloudWatch

1. Go to **CloudWatch → Logs → Log Groups**
2. Search for: `/aws-glue/jobs/country-population-ingestion`
3. Click on it
4. You should see log streams with names like `ingestion-[timestamp]`
5. Click on the log stream to view events

---

## Verify it Worked

Run this command to check if logs are appearing:

```bash
# Check for log streams
aws logs describe-log-streams \
  --log-group-name /aws-glue/jobs/country-population-ingestion \
  --region us-east-1 \
  --query 'logStreams[].logStreamName' \
  --output text
```

You should see output like:
```
ingestion-2024-01-15-10-30-45-xyz
```

---

## Key Points

✅ **Default job parameters** must have logging flags  
✅ **Log group must exist** in CloudWatch  
✅ **Save the job** after adding parameters  
✅ **Wait 30 seconds** after running job for logs to appear  
✅ **Job must complete** (succeed or fail) to show logs  

---

## If Still No Logs

1. **Verify job has been saved** - Go back to the job, check parameters are still there
2. **Check log group exists**:
   ```bash
   aws logs describe-log-groups --log-group-name-prefix "/aws-glue/jobs/"
   ```

3. **Check job status**:
   ```bash
   aws glue get-job --name country-population-ingestion
   ```
   Look for "DefaultArguments" section to verify parameters are saved

4. **Check CloudWatch permissions** - IAM role needs CloudWatch Logs permissions

Done! ✅
