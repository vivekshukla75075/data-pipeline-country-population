#!/bin/bash

set -e

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}========== Creating Step Functions State Machine ==========${NC}"

# Configuration
AWS_REGION=${AWS_REGION:-"us-east-1"}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
STEP_FUNCTIONS_ROLE_NAME="step-functions-role"

echo "AWS Region: $AWS_REGION"
echo "AWS Account ID: $AWS_ACCOUNT_ID"

# Step 1: Verify Lambda functions exist
echo -e "${YELLOW}[1/3] Verifying Lambda functions...${NC}"

LAMBDA_FUNCTIONS=(
  "trigger-ingestion"
  "trigger-validation"
  "trigger-transformation"
  "create-glue-catalog"
  "query-athena"
)

for func in "${LAMBDA_FUNCTIONS[@]}"; do
  if aws lambda get-function --function-name $func --region $AWS_REGION 2>/dev/null; then
    echo -e "${GREEN}✓ Found Lambda function: $func${NC}"
  else
    echo -e "${RED}❌ Lambda function not found: $func${NC}"
    echo "Please ensure all Lambda functions are deployed first"
    exit 1
  fi
done

# Step 2: Create or verify Step Functions role
echo -e "${YELLOW}[2/3] Setting up Step Functions role...${NC}"

STEP_FUNCTIONS_ROLE_ARN="arn:aws:iam::$AWS_ACCOUNT_ID:role/$STEP_FUNCTIONS_ROLE_NAME"

if aws iam get-role --role-name $STEP_FUNCTIONS_ROLE_NAME 2>/dev/null; then
  echo -e "${GREEN}✓ Step Functions role already exists${NC}"
else
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
    }' 2>/dev/null && echo -e "${GREEN}✓ Role created${NC}" || echo -e "${YELLOW}⚠️ Could not create role${NC}"
fi

# Attach Lambda policy
aws iam attach-role-policy \
  --role-name $STEP_FUNCTIONS_ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/AWSLambdaFullAccess 2>/dev/null || \
  echo -e "${YELLOW}⚠️ Could not attach Lambda policy${NC}"

# Step 3: Create or update State Machine
echo -e "${YELLOW}[3/3] Creating Step Functions State Machine...${NC}"

cat > /tmp/state_machine.json <<EOF
{
  "Comment": "ETL Pipeline Orchestration - Ingestion, Validation, Transformation, Catalog, Analytics",
  "StartAt": "IngestData",
  "States": {
    "IngestData": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:$AWS_REGION:$AWS_ACCOUNT_ID:function:trigger-ingestion",
      "TimeoutSeconds": 900,
      "Next": "IngestionWait",
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "Next": "IngestionFailed"
        }
      ]
    },
    "IngestionWait": {
      "Type": "Wait",
      "Seconds": 10,
      "Next": "ValidateData"
    },
    "ValidateData": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:$AWS_REGION:$AWS_ACCOUNT_ID:function:trigger-validation",
      "TimeoutSeconds": 900,
      "Next": "ValidationWait",
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "Next": "ValidationFailed"
        }
      ]
    },
    "ValidationWait": {
      "Type": "Wait",
      "Seconds": 10,
      "Next": "TransformData"
    },
    "TransformData": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:$AWS_REGION:$AWS_ACCOUNT_ID:function:trigger-transformation",
      "TimeoutSeconds": 900,
      "Next": "TransformationWait",
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "Next": "TransformationFailed"
        }
      ]
    },
    "TransformationWait": {
      "Type": "Wait",
      "Seconds": 10,
      "Next": "UpdateDataCatalog"
    },
    "UpdateDataCatalog": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:$AWS_REGION:$AWS_ACCOUNT_ID:function:create-glue-catalog",
      "TimeoutSeconds": 300,
      "Next": "CatalogWait",
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "Next": "CatalogFailed"
        }
      ]
    },
    "CatalogWait": {
      "Type": "Wait",
      "Seconds": 5,
      "Next": "QueryAthena"
    },
    "QueryAthena": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:$AWS_REGION:$AWS_ACCOUNT_ID:function:query-athena",
      "TimeoutSeconds": 300,
      "Next": "Success",
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "Next": "QueryFailed"
        }
      ]
    },
    "Success": {
      "Type": "Succeed"
    },
    "IngestionFailed": {
      "Type": "Fail",
      "Error": "IngestionJobFailed",
      "Cause": "Ingestion Glue job failed"
    },
    "ValidationFailed": {
      "Type": "Fail",
      "Error": "ValidationJobFailed",
      "Cause": "Validation Glue job failed"
    },
    "TransformationFailed": {
      "Type": "Fail",
      "Error": "TransformationJobFailed",
      "Cause": "Transformation Glue job failed"
    },
    "CatalogFailed": {
      "Type": "Fail",
      "Error": "CatalogUpdateFailed",
      "Cause": "Glue Data Catalog update failed"
    },
    "QueryFailed": {
      "Type": "Fail",
      "Error": "AthenaQueryFailed",
      "Cause": "Athena query execution failed"
    }
  }
}
EOF

# Check if state machine already exists
STATE_MACHINE_ARN=$(aws stepfunctions list-state-machines \
  --region $AWS_REGION \
  --query "stateMachines[?name=='country-population-etl-pipeline'].stateMachineArn" \
  --output text 2>/dev/null)

if [ -n "$STATE_MACHINE_ARN" ]; then
  echo "Updating existing State Machine..."
  aws stepfunctions update-state-machine \
    --state-machine-arn $STATE_MACHINE_ARN \
    --definition file:///tmp/state_machine.json \
    --role-arn $STEP_FUNCTIONS_ROLE_ARN \
    --region $AWS_REGION 2>/dev/null && \
    echo -e "${GREEN}✓ State Machine updated${NC}" || \
    echo -e "${YELLOW}⚠️ Could not update State Machine${NC}"
else
  echo "Creating new State Machine..."
  STATE_MACHINE_ARN=$(aws stepfunctions create-state-machine \
    --name country-population-etl-pipeline \
    --definition file:///tmp/state_machine.json \
    --role-arn $STEP_FUNCTIONS_ROLE_ARN \
    --region $AWS_REGION \
    --query 'stateMachineArn' \
    --output text 2>/dev/null)
  
  if [ -n "$STATE_MACHINE_ARN" ]; then
    echo -e "${GREEN}✓ State Machine created: $STATE_MACHINE_ARN${NC}"
  else
    echo -e "${RED}❌ Failed to create State Machine${NC}"
    exit 1
  fi
fi

# Summary
echo -e "${GREEN}"
echo "========== Step Functions Setup Complete =========="
echo ""
echo "State Machine ARN: $STATE_MACHINE_ARN"
echo ""
echo "To trigger the pipeline, run:"
echo "aws stepfunctions start-execution \\"
echo "  --state-machine-arn $STATE_MACHINE_ARN \\"
echo "  --input '{}' \\"
echo "  --region $AWS_REGION"
echo ""
echo "Monitor at:"
echo "https://console.aws.amazon.com/states/home?region=$AWS_REGION#/statemachines"
echo "======================================================"
echo -e "${NC}"
