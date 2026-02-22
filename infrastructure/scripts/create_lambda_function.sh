#!/bin/bash

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║         CREATE LAMBDA FUNCTION FOR INGESTION          ║${NC}"
echo -e "${YELLOW}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"
FUNCTION_NAME="ingest-api-data"
BUCKET="data-pipeline-country-population"
IAM_ROLE="lambda-execution-role"

echo "Configuration:"
echo "  Account ID: $ACCOUNT_ID"
echo "  Region: $REGION"
echo "  Function Name: $FUNCTION_NAME"
echo "  Bucket: $BUCKET"
echo ""

# ============================================================================
# STEP 1: CREATE IAM ROLE FOR LAMBDA
# ============================================================================
echo -e "${YELLOW}[STEP 1] Creating IAM role for Lambda...${NC}"

ROLE_DOCUMENT='{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}'

# Check if role exists
ROLE_EXISTS=$(aws iam get-role --role-name $IAM_ROLE 2>/dev/null || echo "")

if [ -z "$ROLE_EXISTS" ]; then
	echo "Creating role: $IAM_ROLE"
	aws iam create-role \
		--role-name $IAM_ROLE \
		--assume-role-policy-document "$ROLE_DOCUMENT"
	echo -e "${GREEN}✓ Role created${NC}"
else
	echo -e "${GREEN}✓ Role already exists${NC}"
fi

# Wait for role to be available
sleep 2

echo ""

# ============================================================================
# STEP 2: ATTACH S3 POLICY TO ROLE
# ============================================================================
echo -e "${YELLOW}[STEP 2] Attaching S3 policy to Lambda role...${NC}"

S3_POLICY="{
  \"Version\": \"2012-10-17\",
  \"Statement\": [
    {
      \"Effect\": \"Allow\",
      \"Action\": [
        \"s3:GetObject\",
        \"s3:PutObject\",
        \"s3:DeleteObject\",
        \"s3:ListBucket\"
      ],
      \"Resource\": [
        \"arn:aws:s3:::${BUCKET}/*\",
        \"arn:aws:s3:::${BUCKET}\"
      ]
    }
  ]
}"

aws iam put-role-policy \
	--role-name $IAM_ROLE \
	--policy-name S3AccessPolicy \
	--policy-document "$S3_POLICY"

echo -e "${GREEN}✓ S3 policy attached${NC}"
echo ""

# ============================================================================
# STEP 3: ATTACH BASIC LAMBDA EXECUTION POLICY
# ============================================================================
echo -e "${YELLOW}[STEP 3] Attaching basic Lambda execution policy...${NC}"

aws iam attach-role-policy \
	--role-name $IAM_ROLE \
	--policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

echo -e "${GREEN}✓ Basic execution policy attached${NC}"
echo ""

# ============================================================================
# STEP 4: CREATE LAMBDA FUNCTION
# ============================================================================
echo -e "${YELLOW}[STEP 4] Creating Lambda function...${NC}"

ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${IAM_ROLE}"

# Create a minimal Python package for Lambda
cd lambda_deployment

rm -f ingest_api_data.zip
zip -q ingest_api_data.zip ingest_api_data.py

echo "Lambda package size: $(ls -lh ingest_api_data.zip | awk '{print $5}')"

# Check if function exists
FUNCTION_EXISTS=$(aws lambda get-function --function-name $FUNCTION_NAME --region $REGION 2>/dev/null || echo "")

if [ -z "$FUNCTION_EXISTS" ]; then
	echo "Creating Lambda function: $FUNCTION_NAME"
	aws lambda create-function \
		--function-name $FUNCTION_NAME \
		--runtime python3.9 \
		--role $ROLE_ARN \
		--handler ingest_api_data.lambda_handler \
		--zip-file fileb://ingest_api_data.zip \
		--timeout 60 \
		--memory-size 256 \
		--region $REGION
	echo -e "${GREEN}✓ Lambda function created${NC}"
else
	echo -e "${GREEN}✓ Lambda function already exists${NC}"
fi

cd ..
echo ""

# ============================================================================
# STEP 5: VERIFY LAMBDA FUNCTION
# ============================================================================
echo -e "${YELLOW}[STEP 5] Verifying Lambda function...${NC}"

FUNCTION_ARN=$(aws lambda get-function \
	--function-name $FUNCTION_NAME \
	--region $REGION \
	--query 'Configuration.FunctionArn' \
	--output text)

CODE_SIZE=$(aws lambda get-function \
	--function-name $FUNCTION_NAME \
	--region $REGION \
	--query 'Configuration.CodeSize' \
	--output text)

echo "Function ARN: $FUNCTION_ARN"
echo "Code Size: $CODE_SIZE bytes"
echo -e "${GREEN}✓ Lambda function verified${NC}"
echo ""

# ============================================================================
# STEP 6: ADD LAMBDA PERMISSIONS TO IAM USER
# ============================================================================
echo -e "${YELLOW}[STEP 6] Adding Lambda update permissions to IAM user...${NC}"

LAMBDA_POLICY="{
  \"Version\": \"2012-10-17\",
  \"Statement\": [
    {
      \"Effect\": \"Allow\",
      \"Action\": [
        \"lambda:UpdateFunctionCode\",
        \"lambda:GetFunction\",
        \"lambda:GetFunctionConfiguration\",
        \"lambda:InvokeFunction\"
      ],
      \"Resource\": \"arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${FUNCTION_NAME}\"
    }
  ]
}"

aws iam put-user-policy \
	--user-name data-pipeline-country-population \
	--policy-name LambdaUpdatePolicy \
	--policy-document "$LAMBDA_POLICY"

echo -e "${GREEN}✓ Lambda update permissions added to IAM user${NC}"
echo ""

# ============================================================================
# FINAL SUMMARY
# ============================================================================
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           LAMBDA SETUP COMPLETE ✅                    ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

echo "Summary:"
echo "  ✅ IAM role created: $IAM_ROLE"
echo "  ✅ S3 policy attached"
echo "  ✅ Lambda execution policy attached"
echo "  ✅ Lambda function created: $FUNCTION_NAME"
echo "  ✅ Function ARN: $FUNCTION_ARN"
echo "  ✅ IAM user permissions updated"
echo ""

echo "Next steps:"
echo "  1. Push changes to GitHub:"
echo "     git push origin feature/sync-upstream-changes"
echo ""
echo "  2. The GitHub Actions workflow will now:"
echo "     - Deploy Lambda code"
echo "     - Update Glue jobs"
echo "     - Test execution"
echo ""

echo -e "${GREEN}✅ Lambda function is ready for deployment!${NC}"
