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

# Step 1: Create IAM Roles (Optional - May fail due to permissions)
echo -e "${YELLOW}[1/7] Setting up IAM Roles...${NC}"

# Create Lambda Execution Role
echo "Checking Lambda execution role..."
if aws iam get-role --role-name $LAMBDA_ROLE_NAME --region $AWS_REGION 2>/dev/null; then
  echo -e "${GREEN}✓ Lambda role already exists${NC}"
else
  echo "Attempting to create Lambda role..."
  if aws iam create-role \
    --role-name $LAMBDA_ROLE_NAME \
    --assume-role-policy-document '{
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "lambda.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }]
    }' --region $AWS_REGION 2>/dev/null; then
    echo -e "${GREEN}✓ Lambda role created${NC}"
  else
    echo -e "${YELLOW}⚠️ Could not create Lambda role (check permissions)${NC}"
  fi
fi

# Attach policies to Lambda role (continue on error)
echo "Attaching policies to Lambda role..."
aws iam attach-role-policy \
  --role-name $LAMBDA_ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole \
  --region $AWS_REGION 2>/dev/null || echo -e "${YELLOW}⚠️ Could not attach policy (may already be attached)${NC}"

aws iam attach-role-policy \
  --role-name $LAMBDA_ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonGlueFullAccess \
  --region $AWS_REGION 2>/dev/null || echo -e "${YELLOW}⚠️ Could not attach Glue policy${NC}"

# Create Step Functions Role
echo "Checking Step Functions role..."
if aws iam get-role --role-name $STEP_FUNCTIONS_ROLE_NAME --region $AWS_REGION 2>/dev/null; then
  echo -e "${GREEN}✓ Step Functions role already exists${NC}"
else
  echo "Attempting to create Step Functions role..."
  if aws iam create-role \
    --role-name $STEP_FUNCTIONS_ROLE_NAME \
    --assume-role-policy-document '{
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "states.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }]
    }' --region $AWS_REGION 2>/dev/null; then
    echo -e "${GREEN}✓ Step Functions role created${NC}"
  else
    echo -e "${YELLOW}⚠️ Could not create Step Functions role${NC}"
  fi
fi

aws iam attach-role-policy \
  --role-name $STEP_FUNCTIONS_ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/AWSLambdaFullAccess \
  --region $AWS_REGION 2>/dev/null || echo -e "${YELLOW}⚠️ Could not attach Lambda policy to Step Functions role${NC}"

echo -e "${GREEN}✓ IAM Roles setup completed${NC}"

# Step 2: Create Glue Database
echo -e "${YELLOW}[2/7] Creating Glue Database...${NC}"

if aws glue get-database --name country_population --region $AWS_REGION 2>/dev/null; then
  echo -e "${GREEN}✓ Database already exists${NC}"
else
  aws glue create-database \
    --database-input Name=country_population,Description="Country population ETL database" \
    --region $AWS_REGION 2>/dev/null || echo -e "${YELLOW}⚠️ Could not create database${NC}"
fi

echo -e "${GREEN}✓ Glue Database ready${NC}"

# Step 3: Deploy Lambda Functions
echo -e "${YELLOW}[3/7] Deploying Lambda Functions...${NC}"

LAMBDA_ROLE_ARN="arn:aws:iam::$AWS_ACCOUNT_ID:role/$LAMBDA_ROLE_NAME"

deploy_lambda() {
  local function_name=$1
  local handler=$2
  local zip_file=$3
  
  echo "Deploying $function_name..."
  
  if [ ! -f "$zip_file" ]; then
    echo -e "${YELLOW}⚠️ Zip file not found: $zip_file${NC}"
    return 1
  fi
  
  if aws lambda get-function --function-name $function_name --region $AWS_REGION 2>/dev/null; then
    aws lambda update-function-code \
      --function-name $function_name \
      --zip-file fileb://$zip_file \
      --region $AWS_REGION 2>/dev/null && echo -e "${GREEN}✓ Updated $function_name${NC}" || echo -e "${YELLOW}⚠️ Could not update $function_name${NC}"
  else
    aws lambda create-function \
      --function-name $function_name \
      --runtime python3.9 \
      --role $LAMBDA_ROLE_ARN \
      --handler $handler \
      --zip-file fileb://$zip_file \
      --timeout 300 \
      --memory-size 256 \
      --environment "Variables={S3_BUCKET=$S3_BUCKET}" \
      --region $AWS_REGION 2>/dev/null && echo -e "${GREEN}✓ Created $function_name${NC}" || echo -e "${YELLOW}⚠️ Could not create $function_name${NC}"
  fi
}

# Package and deploy lambda functions (continue on error)
if [ -d "lambda_functions/orchestration" ]; then
  cd lambda_functions/orchestration 2>/dev/null
  zip -r lambda_functions.zip . 2>/dev/null || true
  cd ../.. 2>/dev/null
  
  deploy_lambda "trigger-ingestion" "trigger_ingestion.lambda_handler" "lambda_functions/orchestration/lambda_functions.zip"
  deploy_lambda "trigger-validation" "trigger_validation.lambda_handler" "lambda_functions/orchestration/lambda_functions.zip"
  deploy_lambda "trigger-transformation" "trigger_transformation.lambda_handler" "lambda_functions/orchestration/lambda_functions.zip"
  deploy_lambda "query-athena" "query_athena.lambda_handler" "lambda_functions/orchestration/lambda_functions.zip"
else
  echo -e "${YELLOW}⚠️ Lambda functions directory not found${NC}"
fi

if [ -d "lambda_functions/catalog" ]; then
  cd lambda_functions/catalog 2>/dev/null
  zip -r lambda_functions.zip . 2>/dev/null || true
  cd ../.. 2>/dev/null
  deploy_lambda "create-glue-catalog" "create_glue_catalog.lambda_handler" "lambda_functions/catalog/lambda_functions.zip"
else
  echo -e "${YELLOW}⚠️ Catalog lambda directory not found${NC}"
fi

echo -e "${GREEN}✓ Lambda Functions deployment completed${NC}"

# Step 4: Create Glue Jobs
echo -e "${YELLOW}[4/7] Creating Glue Jobs...${NC}"

GLUE_ROLE_ARN="arn:aws:iam::$AWS_ACCOUNT_ID:role/$GLUE_ROLE_NAME"

create_glue_job() {
  local job_name=$1
  local script_location=$2
  
  echo "Creating Glue job: $job_name..."
  
  if aws glue get-job --name $job_name --region $AWS_REGION 2>/dev/null; then
    echo -e "${GREEN}✓ Job already exists: $job_name${NC}"
  else
    aws glue create-job \
      --name $job_name \
      --role $GLUE_ROLE_ARN \
      --command Name=glueetl,ScriptLocation=$script_location \
      --glue-version "3.0" \
      --worker-type G.1X \
      --number-of-workers 3 \
      --region $AWS_REGION 2>/dev/null && echo -e "${GREEN}✓ Created $job_name${NC}" || echo -e "${YELLOW}⚠️ Could not create $job_name${NC}"
  fi
}

create_glue_job "country-population-ingestion" "s3://$S3_BUCKET/scripts/ingest_data.py"
create_glue_job "country-population-validation" "s3://$S3_BUCKET/scripts/validate_schema.py"
create_glue_job "country-population-transformation" "s3://$S3_BUCKET/scripts/transform_data.py"

echo -e "${GREEN}✓ Glue Jobs creation completed${NC}"

# Step 5: Create Athena Workgroup
echo -e "${YELLOW}[5/7] Creating Athena Workgroup...${NC}"

if aws athena get-work-group --name primary --region $AWS_REGION 2>/dev/null; then
  echo -e "${GREEN}✓ Workgroup already exists${NC}"
else
  aws athena create-work-group \
    --name primary \
    --description "Primary workgroup" \
    --configuration ResultConfigurationUpdates="{OutputLocation=s3://$S3_BUCKET/athena-results/}" \
    --region $AWS_REGION 2>/dev/null || echo -e "${YELLOW}⚠️ Could not create workgroup${NC}"
fi

echo -e "${GREEN}✓ Athena Workgroup ready${NC}"

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

if aws stepfunctions describe-state-machine --name country-population-etl-pipeline --region $AWS_REGION 2>/dev/null; then
  echo -e "${GREEN}✓ State Machine already exists${NC}"
else
  aws stepfunctions create-state-machine \
    --name country-population-etl-pipeline \
    --definition file:///tmp/state_machine.json \
    --role-arn $STEP_FUNCTIONS_ROLE_ARN \
    --region $AWS_REGION 2>/dev/null && echo -e "${GREEN}✓ State Machine created${NC}" || echo -e "${YELLOW}⚠️ Could not create State Machine${NC}"
fi

echo -e "${GREEN}✓ Step Functions State Machine ready${NC}"

# Step 7: Create Athena Tables
echo -e "${YELLOW}[7/7] Creating Athena Tables...${NC}"

aws athena start-query-execution \
  --query-string "CREATE EXTERNAL TABLE IF NOT EXISTS country_population.countries_curated (country_name STRING, subregion STRING, population BIGINT, area DOUBLE, capital_city STRING, currency STRING) PARTITIONED BY (region STRING) STORED AS PARQUET LOCATION 's3://$S3_BUCKET/curated/countries/' TBLPROPERTIES ('classification'='parquet')" \
  --query-execution-context Database=country_population \
  --result-configuration OutputLocation=s3://$S3_BUCKET/athena-results/ \
  --region $AWS_REGION 2>/dev/null || echo -e "${YELLOW}⚠️ Could not create table (may already exist)${NC}"

echo -e "${GREEN}✓ Athena Tables ready${NC}"

# Summary
echo -e "${GREEN}"
echo "========== Deployment Summary =========="
echo "AWS Region: $AWS_REGION"
echo "S3 Bucket: $S3_BUCKET"
echo "Glue Database: country_population"
echo ""
echo "Next Steps:"
echo "1. Ask AWS admin to grant permission: iam:AttachRolePolicy (if needed)"
echo "2. Trigger pipeline with:"
echo "   aws stepfunctions start-execution \\"
echo "   --state-machine-arn arn:aws:states:$AWS_REGION:$AWS_ACCOUNT_ID:stateMachine:country-population-etl-pipeline \\"
echo "   --input '{}'"
echo ""
echo "Verify resources in AWS Console"
echo "================================"
echo -e "${NC}"
