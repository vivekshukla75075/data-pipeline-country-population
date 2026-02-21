# Automated Deployment Guide

## Overview

The entire ETL pipeline is deployed automatically via GitHub Actions. No manual AWS Console steps required.

## Prerequisites

1. **GitHub Secrets** (already configured):
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`

2. **AWS S3 Bucket** (must exist):
   - `data-pipeline-country-population`

3. **AWS IAM User Permissions**:
   - S3, Glue, Lambda, Step Functions, IAM, Athena

## Deployment Process

### Option 1: Automatic (Recommended)

**Push code to GitHub:**
```bash
git push origin feature/sync-upstream-changes
```

The workflow will automatically:
- Build and test the code
- Upload scripts to S3
- Create IAM roles
- Create Glue jobs
- Create Lambda functions
- Create Step Functions state machine
- Create Athena tables

### Option 2: Manual Deployment

**Run deployment script locally:**
```bash
chmod +x infrastructure/scripts/deploy_pipeline.sh
./infrastructure/scripts/deploy_pipeline.sh
```

## What Gets Deployed

### 1. IAM Roles
- `lambda-execution-role`: For Lambda functions
- `step-functions-role`: For Step Functions

### 2. Glue Jobs
- `country-population-ingestion`: Fetches API data
- `country-population-validation`: Validates data
- `country-population-transformation`: Transforms data

### 3. Lambda Functions
- `trigger-ingestion`: Triggers ingestion Glue job
- `trigger-validation`: Triggers validation Glue job
- `trigger-transformation`: Triggers transformation Glue job
- `create-glue-catalog`: Creates Glue Data Catalog
- `query-athena`: Executes Athena queries

### 4. Step Functions
- `country-population-etl-pipeline`: Orchestrates entire workflow

### 5. Athena
- Workgroup: `primary`
- Table: `country_population.countries_curated`

## Triggering the Pipeline

### Via AWS Console
1. Go to Step Functions
2. Click on `country-population-etl-pipeline`
3. Click **Start execution**
4. Click **Start execution** again

### Via AWS CLI
```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:YOUR_ACCOUNT_ID:stateMachine:country-population-etl-pipeline \
  --input '{}'
```

### Via GitHub Actions (CI/CD)
- Push code: automatically triggers workflow
- Workflow uploads scripts and can trigger pipeline

## Monitoring

### CloudWatch Logs
```bash
# View all logs
aws logs tail /aws/lambda/ --follow

# View specific function
aws logs tail /aws/lambda/trigger-ingestion --follow
```

### Step Functions Console
- View execution history
- Monitor each step status
- Check error details

### Glue Console
- View job runs
- Check job output
- Monitor job metrics

## Troubleshooting

### Deployment Failed
```bash
# Check GitHub Actions logs
# Go to Actions tab → workflow run → logs

# Re-run deployment script
./infrastructure/scripts/deploy_pipeline.sh
```

### Pipeline Execution Failed
```bash
# Check Step Functions execution
aws stepfunctions describe-execution \
  --execution-arn <EXECUTION_ARN>

# View Glue job logs
aws logs tail /aws-glue/jobs/country-population-validation --follow
```

### Lambda Function Failed
```bash
# Check Lambda logs
aws logs tail /aws/lambda/trigger-ingestion --follow

# Check Lambda error details
aws lambda get-function-code-signing-config --function-name trigger-ingestion
```

## Cost Estimation

**Approximate monthly costs:**
- Glue: 3 jobs × 0.44/DPU-hour = ~$30-50
- Lambda: 5 functions × $0.20/1M requests = ~$1-5
- S3: Data storage + requests = ~$5-10
- Athena: $6.25/TB scanned = ~$1-5

**Total: ~$40-70/month**

## Next Steps

1. Verify deployment in AWS Console
2. Upload sample data to S3
3. Trigger pipeline via Step Functions
4. Monitor execution via CloudWatch
5. Query results in Athena
6. Create QuickSight dashboards
