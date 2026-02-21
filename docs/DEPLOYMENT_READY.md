# Deployment Ready ✅

## Current Status

- ✅ S3 bucket created: `data-pipeline-country-population`
- ✅ IAM policy created: `DataPipelineDeploymentPolicyupd`
- ⏳ Policy needs to be attached to user

---

## Admin: Final Step - Attach Policy

**Run this ONE command:**

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text) && \
aws iam attach-user-policy \
  --user-name data-pipeline-country-population \
  --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/DataPipelineDeploymentPolicyupd && \
echo "✅ Policy attached successfully!"
```

**Verify:**

```bash
aws iam list-attached-user-policies --user-name data-pipeline-country-population
```

---

## User: Deploy the Pipeline

Once admin attaches the policy, you can run:

```bash
chmod +x infrastructure/scripts/full_deployment.sh
./infrastructure/scripts/full_deployment.sh
```

**This will automatically:**
- Create Glue jobs
- Create Lambda functions  
- Create Step Functions
- Create Athena tables
- Upload all scripts to S3

**Complete ETL pipeline in one command!** 🚀

---

## Then: Run the Pipeline

```bash
# Upload sample data
aws s3 cp sample_data.json s3://data-pipeline-country-population/raw/countries/countries_raw.json

# Trigger pipeline
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:$ACCOUNT_ID:stateMachine:country-population-etl-pipeline \
  --input '{}'
```

---

## Query Results

```sql
SELECT region, SUM(population) AS total_population
FROM country_population.countries_curated
GROUP BY region
ORDER BY total_population DESC;
```

---

## Done! 🎉

You have a production-ready ETL pipeline on AWS!
