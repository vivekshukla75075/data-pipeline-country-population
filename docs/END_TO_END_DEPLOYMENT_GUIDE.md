# End-to-End Deployment Guide

This guide covers the complete deployment of the data pipeline infrastructure from ingestion through transformation to table creation, including all components (S3, Lambda, Step Functions, Glue ETL, SNS, SQS).

## Architecture Overview

```
EventBridge Schedule
         ↓
    Step Functions State Machine
         ↓
    Lambda: ingest-api-data (fetches country data)
         ↓
    S3 Raw Zone (raw/countries/)
         ↓
    Glue Job: country-population-validation (validate schema)
         ↓
    S3 Validated Zone (validated/countries/)
         ↓
    Glue Job: country-population-intermediate (transform structure)
         ↓
    S3 Intermediate Zone (intermediate/countries/)
         ↓
    Glue Job: country-population-transformation (curate data)
         ↓
    S3 Curated Zone (curated/countries/)
         ↓
    Athena Table (query curated data)
```

## Deployment Components

### 1. **CloudFormation Stack (orchestration.yaml)**
Creates the foundational infrastructure:

| Resource | Purpose | Details |
|----------|---------|---------|
| S3 Bucket | Data lake storage | Versioning enabled, AES256 encryption |
| Lambda: ingest-api-data | API ingestion | Fetches from restcountries.com API |
| Lambda: pipeline-status-notifier | Status notifications | Sends to SNS/SQS |
| Glue Jobs (3) | ETL processing | Validation, Intermediate, Transformation |
| SQS Queues (2) | Message routing | Validation trigger, Notifications |
| SNS Topic | Email notifications | Sends pipeline status emails |
| Step Functions | Orchestration | Coordinates all jobs with retry logic |
| EventBridge Rule | Scheduling | Triggers pipeline on schedule (default: daily) |

### 2. **Deploy Workflow (02-deploy.yml)**
GitHub Actions workflow that:

1. Validates CloudFormation template
2. Builds Lambda packages (ingest_api_data.zip, notify_pipeline_status.zip)
3. Deploys CloudFormation stack
4. **Uploads Glue scripts to S3 bucket** (NEW)
5. **Creates/updates Glue jobs with correct configurations** (NEW)
6. **Bootstraps S3 folder structure** (NEW)
7. Deploys Lambda functions with environment variables

### 3. **Glue ETL Jobs**
Three production Glue jobs created automatically by deploy workflow:

#### Job 1: country-population-validation
- **Input**: `s3://data-pipeline-{env}-{account}/raw/countries/`
- **Processing**: 
  - Validates required fields (name, population, region)
  - Checks data quality (non-null populations > 0)
  - Filters corrupt records
- **Output**: `s3://data-pipeline-{env}-{account}/validated/countries/`
- **Format**: Parquet (partitioned by region)
- **Archive**: Moves raw JSON to archive/ after validation

#### Job 2: country-population-intermediate
- **Input**: `s3://data-pipeline-{env}-{account}/validated/countries/`
- **Processing**:
  - Flattens nested JSON structures
  - Extracts capital city from array
  - Converts currencies to JSON strings
  - Casts population to long, area to double
- **Output**: `s3://data-pipeline-{env}-{account}/intermediate/countries/`
- **Format**: Parquet (partitioned by region)

#### Job 3: country-population-transformation
- **Input**: `s3://data-pipeline-{env}-{account}/intermediate/countries/`
- **Processing**:
  - Selects curated columns (country_name, region, population, area, capital, currency)
  - Adds load_date (current date)
  - Final data quality checks
- **Output**: `s3://data-pipeline-{env}-{account}/curated/countries/`
- **Format**: Parquet (partitioned by region)

### 4. **Standalone Test Glue Job (Independent)**
For PySpark/DataFrame/Spark SQL validation:

**Files**:
- `infra/cloudformation/glue-test-job-resources.yaml` - Creates test S3 bucket + IAM role
- `scripts/glue_test_job.py` - Comprehensive test script

**Capabilities**:
- ✅ DataFrame API transformations (column operations, filtering, type casting)
- ✅ Spark SQL aggregations (COUNT, AVG, MAX, MIN, GROUP BY, Window functions)
- ✅ Multiple input formats (CSV, Parquet, JSON)
- ✅ Data quality tests (null checks, distinct values)
- ✅ String operations (upper, lower, trim, regexp)

**Deploy Test Infrastructure**:

```bash
# 1. Deploy test stack (creates separate bucket and role)
aws cloudformation deploy \
  --template-file infra/cloudformation/glue-test-job-resources.yaml \
  --stack-name data-pipeline-glue-test \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides Environment=dev \
  --region us-east-1

# 2. Get outputs
BUCKET=$(aws cloudformation describe-stacks \
  --stack-name data-pipeline-glue-test \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`GlueTestBucketName`].OutputValue' \
  --output text)

ROLE_ARN=$(aws cloudformation describe-stacks \
  --stack-name data-pipeline-glue-test \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`GlueJobRoleArn`].OutputValue' \
  --output text)

echo "Test Bucket: $BUCKET"
echo "Test Role: $ROLE_ARN"

# 3. Upload test script and sample data
aws s3 cp scripts/glue_test_job.py s3://$BUCKET/glue-scripts/
aws s3 cp output/raw/countries/*.json s3://$BUCKET/input/

# 4. Create test Glue job
aws glue create-job \
  --name glue-test-job \
  --role $ROLE_ARN \
  --command Name=gluetl,ScriptLocation=s3://$BUCKET/glue-scripts/glue_test_job.py \
  --glue-version 3.0 \
  --worker-type G.1X \
  --number-of-workers 2 \
  --region us-east-1

# 5. Run test job
aws glue start-job-run \
  --job-name glue-test-job \
  --arguments='--JOB_NAME=glue-test-job,--INPUT_PATH=s3://'$BUCKET'/input/,--OUTPUT_PATH=s3://'$BUCKET'/output/,--INPUT_FORMAT=json' \
  --region us-east-1
```

**Monitor Test Job**:

```bash
# Check job run status
aws glue get-job-run \
  --job-name glue-test-job \
  --run-id <run-id> \
  --region us-east-1

# View CloudWatch logs
aws logs describe-log-streams \
  --log-group-name /aws-glue \
  --region us-east-1 \
  --max-items 5

# Tail log stream
aws logs get-log-events \
  --log-group-name /aws-glue \
  --log-stream-name <stream-name> \
  --region us-east-1
```

## Full Deployment Steps

### Step 1: Destroy Any Existing Stack (if needed)

```bash
# GitHub Actions workflow
# Go to Actions → "3. Destroy AWS Resources" → Run workflow
# OR run manually
python scripts/empty_s3_bucket.py data-pipeline-orchestration-${ACCOUNT_ID}
aws cloudformation delete-stack --stack-name data-pipeline-orchestration --region us-east-1
```

### Step 2: Deploy Main Pipeline Stack

```bash
# Option A: GitHub Actions (Recommended)
# Push to main/master branch or manually trigger:
# Go to Actions → "2. Deploy to AWS" → Run workflow

# Option B: Manual deployment
export ENVIRONMENT=dev
export AWS_REGION=us-east-1
export STACK_NAME=data-pipeline-orchestration

aws cloudformation deploy \
  --template-file infra/cloudformation/orchestration.yaml \
  --stack-name $STACK_NAME \
  --parameter-overrides Environment=$ENVIRONMENT \
  --capabilities CAPABILITY_NAMED_IAM \
  --region $AWS_REGION

# Verify deployment
aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $AWS_REGION \
  --query 'Stacks[0].StackStatus'
```

### Step 3: Get Stack Outputs

```bash
STACK_NAME=data-pipeline-orchestration
AWS_REGION=us-east-1

BUCKET=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $AWS_REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`DataBucketName`].OutputValue' \
  --output text)

STATE_MACHINE_ARN=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $AWS_REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`StateMachineArn`].OutputValue' \
  --output text)

echo "Data Bucket: $BUCKET"
echo "State Machine: $STATE_MACHINE_ARN"
```

### Step 4: Verify All Components

```bash
# ✅ Check S3 bucket structure
aws s3 ls s3://$BUCKET/ --recursive

# ✅ Check Lambda functions
aws lambda list-functions --region us-east-1 --query 'Functions[?contains(FunctionName, `ingest`) || contains(FunctionName, `notifier`)]'

# ✅ Check Glue jobs
aws glue list-jobs --region us-east-1 --query 'JobNames' | grep country-population

# ✅ Check SQS queues
aws sqs list-queues --region us-east-1 --query 'QueueUrls' | grep data-pipeline

# ✅ Check SNS topics
aws sns list-topics --region us-east-1 --query 'Topics' | grep data-pipeline

# ✅ Check Step Functions
aws stepfunctions list-state-machines --region us-east-1 --query 'StateMachines[?contains(name, `country-population`)]'
```

### Step 5: Trigger Pipeline Manually (Optional Testing)

```bash
# Start execution
EXECUTION_ARN=$(aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --region us-east-1 \
  --query 'executionArn' \
  --output text)

echo "Execution: $EXECUTION_ARN"

# Monitor execution
aws stepfunctions describe-execution \
  --execution-arn $EXECUTION_ARN \
  --region us-east-1
```

### Step 6: Query Results in Athena (After Pipeline Completes)

```bash
# Create Athena database (if needed)
aws athena start-query-execution \
  --query-string "CREATE DATABASE IF NOT EXISTS country_population;" \
  --result-configuration OutputLocation=s3://$BUCKET/athena-results/ \
  --region us-east-1

# Create external table for curated data
aws athena start-query-execution \
  --query-string "
  CREATE EXTERNAL TABLE IF NOT EXISTS country_population.countries_curated (
    country_name STRING,
    region STRING,
    subregion STRING,
    population BIGINT,
    area DOUBLE,
    capital_city STRING,
    currency STRING,
    load_date DATE
  )
  PARTITIONED BY (region STRING)
  STORED AS PARQUET
  LOCATION 's3://$BUCKET/curated/countries/'
  " \
  --result-configuration OutputLocation=s3://$BUCKET/athena-results/ \
  --region us-east-1

# Query curated data
aws athena start-query-execution \
  --query-string "SELECT * FROM country_population.countries_curated LIMIT 10;" \
  --result-configuration OutputLocation=s3://$BUCKET/athena-results/ \
  --region us-east-1
```

## Testing & Validation

### Test 1: Ingestion Lambda
```bash
# Invoke ingestion Lambda
aws lambda invoke \
  --function-name ingest-api-data \
  --payload '{}' \
  --region us-east-1 \
  response.json

cat response.json
```

### Test 2: Validate Glue Script
```bash
# Test on local machine first
python Validation/validate_schema.py

# Or test standalone Glue job for PySpark validation
# See "Standalone Test Glue Job" section above
```

### Test 3: Transformation Pipeline
```bash
# Monitor Step Functions execution
aws stepfunctions describe-execution \
  --execution-arn $EXECUTION_ARN \
  --region us-east-1

# View Glue job logs
aws logs describe-log-groups --log-group-name-prefix '/aws-glue' --region us-east-1
aws logs describe-log-streams --log-group-name '/aws-glue/jobs/country-population-validation' --region us-east-1
```

## Troubleshooting

### Issue: S3 bucket not found
**Solution**: Verify bucket name matches account ID format
```bash
aws s3 ls | grep data-pipeline
```

### Issue: Lambda environment variable error
**Solution**: Check KMS key policy if using encrypted environment variables
```bash
aws lambda get-function-configuration --function-name ingest-api-data --region us-east-1
```

### Issue: Glue job fails
**Solution**: Check CloudWatch logs for specific error
```bash
aws logs get-log-events \
  --log-group-name '/aws-glue/jobs/country-population-validation' \
  --log-stream-name <stream-name> \
  --region us-east-1
```

### Issue: Step Functions fails
**Solution**: Check IAM role permissions and Lambda invocation
```bash
aws stepfunctions describe-execution \
  --execution-arn $EXECUTION_ARN \
  --region us-east-1 \
  --query 'executionHistory' | grep -i error
```

## Cleanup

To remove all resources:

```bash
# 1. Destroy test Glue job stack
aws cloudformation delete-stack \
  --stack-name data-pipeline-glue-test \
  --region us-east-1

# 2. Empty and delete main stack
python scripts/empty_s3_bucket.py data-pipeline-orchestration-${ACCOUNT_ID}

aws cloudformation delete-stack \
  --stack-name data-pipeline-orchestration \
  --region us-east-1

# 3. Verify deletion
aws cloudformation describe-stacks \
  --stack-name data-pipeline-orchestration \
  --region us-east-1
```

## Summary

✅ **Components Deployed**:
- S3 Data Lake (raw, validated, intermediate, curated zones)
- Lambda Functions (ingestion, notifications)
- Glue ETL Jobs (3 jobs: validation → intermediate → transformation)
- Step Functions (orchestration with retries)
- SQS Queues (validation trigger, notifications)
- SNS Topic (email alerts)
- EventBridge Rule (daily scheduling)
- Standalone Test Glue Job (PySpark/SQL validation)

✅ **Data Flow**:
1. **Ingestion**: Lambda fetches country data from API → raw S3
2. **Validation**: Glue validates schema, quality → validated S3
3. **Intermediate**: Glue flattens structures → intermediate S3
4. **Transformation**: Glue curates final dataset → curated S3
5. **Query**: Athena queries curated Parquet tables

✅ **Independent Testing**:
- Standalone test Glue job for PySpark DataFrame & Spark SQL validation
- Can be deployed separately to test transformations
- Includes comprehensive DataFrame API and SQL examples
