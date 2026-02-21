#!/bin/bash

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION=${AWS_REGION:-"us-east-1"}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
S3_BUCKET="data-pipeline-country-population"
GLUE_ROLE_NAME="glue-validation-role"
LAMBDA_ROLE_NAME="lambda-execution-role"
STEP_FUNCTIONS_ROLE_NAME="step-functions-role"

echo -e "${YELLOW}========== ETL Pipeline Automated Deployment ==========${NC}"
echo "AWS Region: $AWS_REGION"
echo "AWS Account ID: $AWS_ACCOUNT_ID"
echo "S3 Bucket: $S3_BUCKET"

# Step 1: Create IAM Roles
echo -e "${YELLOW}[1/7] Creating IAM Roles...${NC}"

# Create Lambda Execution Role
echo "Creating Lambda execution role..."
aws iam create-role \
  --role-name $LAMBDA_ROLE_NAME \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }' --region $AWS_REGION 2>/dev/null || echo -e "${GREEN}Role already exists${NC}"

# Attach policies to Lambda role
aws iam attach-role-policy \
  --role-name $LAMBDA_ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy \
  --role-name $LAMBDA_ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonGlueFullAccess

# Create Step Functions Role
echo "Creating Step Functions role..."
aws iam create-role \
  --role-name $STEP_FUNCTIONS_ROLE_NAME \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "states.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }' 2>/dev/null || echo -e "${GREEN}Role already exists${NC}"

aws iam attach-role-policy \
  --role-name $STEP_FUNCTIONS_ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/AWSLambdaFullAccess

echo -e "${GREEN}✓ IAM Roles created${NC}"

# Step 2: Create Glue Database
echo -e "${YELLOW}[2/7] Creating Glue Database...${NC}"

aws glue create-database \
  --database-input Name=country_population,Description="Country population ETL database" \
  --region $AWS_REGION 2>/dev/null || echo -e "${GREEN}Database already exists${NC}"

echo -e "${GREEN}✓ Glue Database created${NC}"

# Step 3: Deploy Lambda Functions
echo -e "${YELLOW}[3/7] Deploying Lambda Functions...${NC}"

LAMBDA_ROLE_ARN="arn:aws:iam::$AWS_ACCOUNT_ID:role/$LAMBDA_ROLE_NAME"

# Function to deploy Lambda
deploy_lambda() {
  local function_name=$1
  local handler=$2
  local zip_file=$3
  
  echo "Deploying $function_name..."
  
  # Check if zip file exists
  if [ ! -f "$zip_file" ]; then
    echo -e "${YELLOW}⚠️ Zip file not found: $zip_file${NC}"
    return 1
  fi
  
  if aws lambda get-function --function-name $function_name --region $AWS_REGION 2>/dev/null; then
    aws lambda update-function-code \
      --function-name $function_name \
      --zip-file fileb://$zip_file \
      --region $AWS_REGION 2>/dev/null || echo -e "${YELLOW}⚠️ Could not update function${NC}"
  else
    aws lambda create-function \
      --function-name $function_name \
      --runtime python3.9 \
      --role $LAMBDA_ROLE_ARN \
      --handler $handler \
      --zip-file fileb://$zip_file \
      --timeout 300 \
      --memory-size 256 \
      --environment "Variables={S3_BUCKET=$S3_BUCKET,GLUE_INGESTION_JOB=country-population-ingestion,GLUE_VALIDATION_JOB=country-population-validation,GLUE_TRANSFORMATION_JOB=country-population-transformation}" \
      --region $AWS_REGION 2>/dev/null || echo -e "${YELLOW}⚠️ Could not create function${NC}"
  fi
}

# Package lambda functions (if directory exists)
if [ -d "lambda_functions/orchestration" ]; then
  cd lambda_functions/orchestration
  zip -r lambda_functions.zip . 2>/dev/null || true
  cd ../..
  
  deploy_lambda "trigger-ingestion" "trigger_ingestion.lambda_handler" "lambda_functions/orchestration/lambda_functions.zip"
  deploy_lambda "trigger-validation" "trigger_validation.lambda_handler" "lambda_functions/orchestration/lambda_functions.zip"
  deploy_lambda "trigger-transformation" "trigger_transformation.lambda_handler" "lambda_functions/orchestration/lambda_functions.zip"
  deploy_lambda "query-athena" "query_athena.lambda_handler" "lambda_functions/orchestration/lambda_functions.zip"
else
  echo -e "${YELLOW}⚠️ Lambda functions directory not found${NC}"
fi

if [ -d "lambda_functions/catalog" ]; then
  cd lambda_functions/catalog
  zip -r lambda_functions.zip . 2>/dev/null || true
  cd ../..
  deploy_lambda "create-glue-catalog" "create_glue_catalog.lambda_handler" "lambda_functions/catalog/lambda_functions.zip"
else
  echo -e "${YELLOW}⚠️ Catalog lambda directory not found${NC}"
fi

echo -e "${GREEN}✓ Lambda Functions deployment completed${NC}"

# Step 4: Create Glue Jobs
echo -e "${YELLOW}[4/7] Creating Glue Jobs...${NC}"

GLUE_ROLE_ARN="arn:aws:iam::$AWS_ACCOUNT_ID:role/$GLUE_ROLE_NAME"

# Function to create Glue job
create_glue_job() {
  local job_name=$1
  local script_location=$2
  
  echo "Creating Glue job: $job_name..."
  
  aws glue create-job \
    --name $job_name \
    --role $GLUE_ROLE_ARN \
    --command Name=glueetl,ScriptLocation=$script_location \
    --glue-version "3.0" \
    --worker-type G.1X \
    --number-of-workers 3 \
    --region $AWS_REGION 2>/dev/null || echo -e "${GREEN}Job already exists${NC}"
}

create_glue_job "country-population-ingestion" "s3://$S3_BUCKET/scripts/ingest_data.py"
create_glue_job "country-population-validation" "s3://$S3_BUCKET/scripts/validate_schema.py"
create_glue_job "country-population-transformation" "s3://$S3_BUCKET/scripts/transform_data.py"

echo -e "${GREEN}✓ Glue Jobs created${NC}"

# Step 5: Create Athena Workgroup
echo -e "${YELLOW}[5/7] Creating Athena Workgroup...${NC}"

aws athena create-work-group \
  --name primary \
  --description "Primary workgroup" \
  --configuration ResultConfigurationUpdates="{OutputLocation=s3://$S3_BUCKET/athena-results/}" \
  --region $AWS_REGION 2>/dev/null || echo -e "${GREEN}Workgroup already exists${NC}"

echo -e "${GREEN}✓ Athena Workgroup created${NC}"

# Step 6: Create Step Functions State Machine
echo -e "${YELLOW}[6/7] Creating Step Functions State Machine...${NC}"

STEP_FUNCTIONS_ROLE_ARN="arn:aws:iam::$AWS_ACCOUNT_ID:role/$STEP_FUNCTIONS_ROLE_NAME"

cat > /tmp/state_machine.json <<EOF
{
  "Comment": "ETL Pipeline Orchestration",
  "StartAt": "IngestData",
  "States": {
    "IngestData": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:$AWS_REGION:$AWS_ACCOUNT_ID:function:trigger-ingestion",
      "Next": "ValidateData",
      "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "ErrorHandler"}]
    },
    "ValidateData": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:$AWS_REGION:$AWS_ACCOUNT_ID:function:trigger-validation",
      "Next": "TransformData",
      "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "ErrorHandler"}]
    },
    "TransformData": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:$AWS_REGION:$AWS_ACCOUNT_ID:function:trigger-transformation",
      "Next": "UpdateDataCatalog",
      "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "ErrorHandler"}]
    },
    "UpdateDataCatalog": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:$AWS_REGION:$AWS_ACCOUNT_ID:function:create-glue-catalog",
      "Next": "QueryAthena",
      "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "ErrorHandler"}]
    },
    "QueryAthena": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:$AWS_REGION:$AWS_ACCOUNT_ID:function:query-athena",
      "Next": "Success",
      "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "ErrorHandler"}]
    },
    "Success": {"Type": "Succeed"},
    "ErrorHandler": {"Type": "Fail"}
  }
}
EOF

aws stepfunctions create-state-machine \
  --name country-population-etl-pipeline \
  --definition file:///tmp/state_machine.json \
  --role-arn $STEP_FUNCTIONS_ROLE_ARN \
  --region $AWS_REGION 2>/dev/null || echo -e "${GREEN}State Machine already exists${NC}"

echo -e "${GREEN}✓ Step Functions State Machine created${NC}"

# Summary
echo -e "${GREEN}"
echo "========== Deployment Complete =========="
echo "Summary:"
echo "- AWS Region: $AWS_REGION"
echo "- S3 Bucket: $S3_BUCKET"
echo "- Glue Database: country_population"
echo "- Glue Jobs: 3 created"
echo "- Lambda Functions: 5 created"
echo "- Step Functions: country-population-etl-pipeline"
echo ""
echo "To trigger the pipeline, run:"
echo "aws stepfunctions start-execution \\"
echo "  --state-machine-arn arn:aws:states:$AWS_REGION:$AWS_ACCOUNT_ID:stateMachine:country-population-etl-pipeline \\"
echo "  --input '{}'"
echo "========================================="
echo -e "${NC}"
