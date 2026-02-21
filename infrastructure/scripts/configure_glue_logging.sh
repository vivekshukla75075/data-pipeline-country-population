#!/bin/bash

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}========== Configuring Glue Job Logging ==========${NC}"

AWS_REGION="us-east-1"

# Create CloudWatch log groups
echo -e "${YELLOW}Creating CloudWatch log groups...${NC}"

aws logs create-log-group \
  --log-group-name /aws-glue/jobs/country-population-ingestion \
  --region $AWS_REGION 2>/dev/null || echo "Log group already exists"

aws logs create-log-group \
  --log-group-name /aws-glue/jobs/country-population-validation \
  --region $AWS_REGION 2>/dev/null || echo "Log group already exists"

aws logs create-log-group \
  --log-group-name /aws-glue/jobs/country-population-transformation \
  --region $AWS_REGION 2>/dev/null || echo "Log group already exists"

echo -e "${GREEN}✓ Log groups created${NC}"

# Create Glue jobs with proper logging configuration
echo -e "${YELLOW}Updating Glue jobs with logging configuration...${NC}"

BUCKET_NAME="data-pipeline-country-population"
ROLE_ARN="arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/glue-validation-role"

# Update ingestion job
aws glue update-job \
  --name country-population-ingestion \
  --job-command Name=glueetl,ScriptLocation=s3://$BUCKET_NAME/scripts/ingest_data.py \
  --role $ROLE_ARN \
  --glue-version "3.0" \
  --worker-type G.1X \
  --number-of-workers 3 \
  --default-arguments '{
    "--TempDir": "s3://'$BUCKET_NAME'/temp/",
    "--job-bookmark-option": "job-bookmark-enable",
    "--enable-metrics": "true",
    "--enable-continuous-cloudwatch-log": "true",
    "--continuous-log-logGroup": "/aws-glue/jobs/country-population-ingestion",
    "--continuous-log-logStreamPrefix": "ingestion"
  }' \
  --region $AWS_REGION 2>/dev/null || echo "Job update failed or job doesn't exist"

# Update validation job
aws glue update-job \
  --name country-population-validation \
  --job-command Name=glueetl,ScriptLocation=s3://$BUCKET_NAME/scripts/validate_schema.py \
  --role $ROLE_ARN \
  --glue-version "3.0" \
  --worker-type G.1X \
  --number-of-workers 3 \
  --default-arguments '{
    "--TempDir": "s3://'$BUCKET_NAME'/temp/",
    "--job-bookmark-option": "job-bookmark-enable",
    "--enable-metrics": "true",
    "--enable-continuous-cloudwatch-log": "true",
    "--continuous-log-logGroup": "/aws-glue/jobs/country-population-validation",
    "--continuous-log-logStreamPrefix": "validation"
  }' \
  --region $AWS_REGION 2>/dev/null || echo "Job update failed or job doesn't exist"

# Update transformation job
aws glue update-job \
  --name country-population-transformation \
  --job-command Name=glueetl,ScriptLocation=s3://$BUCKET_NAME/scripts/transform_data.py \
  --role $ROLE_ARN \
  --glue-version "3.0" \
  --worker-type G.1X \
  --number-of-workers 5 \
  --default-arguments '{
    "--TempDir": "s3://'$BUCKET_NAME'/temp/",
    "--job-bookmark-option": "job-bookmark-enable",
    "--enable-metrics": "true",
    "--enable-continuous-cloudwatch-log": "true",
    "--continuous-log-logGroup": "/aws-glue/jobs/country-population-transformation",
    "--continuous-log-logStreamPrefix": "transformation"
  }' \
  --region $AWS_REGION 2>/dev/null || echo "Job update failed or job doesn't exist"

echo -e "${GREEN}✓ Glue jobs updated with logging configuration${NC}"

# Verify log groups exist
echo -e "${YELLOW}Verifying log groups...${NC}"

aws logs describe-log-groups \
  --log-group-name-prefix "/aws-glue/jobs/" \
  --region $AWS_REGION \
  --query 'logGroups[].logGroupName' \
  --output text

echo -e "${GREEN}"
echo "========== Glue Logging Configuration Complete =========="
echo "Log groups created:"
echo "- /aws-glue/jobs/country-population-ingestion"
echo "- /aws-glue/jobs/country-population-validation"
echo "- /aws-glue/jobs/country-population-transformation"
echo ""
echo "You can now view logs in CloudWatch:"
echo "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logStream:"
echo "=============================================================="
echo -e "${NC}"
