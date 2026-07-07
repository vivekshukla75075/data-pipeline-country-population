#!/bin/bash

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}========== DEPLOYING LAMBDA FUNCTION ==========${NC}"

# Get configuration
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"
BUCKET="data-pipeline-country-population"

echo "Account ID: $ACCOUNT_ID"
echo "Region: $REGION"
echo "Bucket: $BUCKET"

# Step 1: Create Lambda ZIP
echo -e "${YELLOW}Step 1: Creating Lambda package...${NC}"
cd lambda_deployment

# Remove old ZIP if exists
rm -f ingest_api_data.zip

# Create new ZIP
zip -q ingest_api_data.zip ingest_api_data.py

echo -e "${GREEN}✓ Lambda package created${NC}"

# Step 2: Create or Update Lambda Function
echo -e "${YELLOW}Step 2: Deploying Lambda function...${NC}"

# Try to create function (will fail if exists)
aws lambda create-function \
  --function-name ingest-api-data \
  --runtime python3.9 \
  --role arn:aws:iam::$ACCOUNT_ID:role/lambda-execution-role \
  --handler ingest_api_data.lambda_handler \
  --zip-file fileb://ingest_api_data.zip \
  --timeout 60 \
  --memory-size 256 \
  --region $REGION 2>/dev/null && echo -e "${GREEN}✓ Lambda function created${NC}" || \
# If create fails, update function
aws lambda update-function-code \
  --function-name ingest-api-data \
  --zip-file fileb://ingest_api_data.zip \
  --region $REGION && echo -e "${GREEN}✓ Lambda function updated${NC}"

# Step 3: Verify
echo -e "${YELLOW}Step 3: Verifying deployment...${NC}"
aws lambda get-function \
  --function-name ingest-api-data \
  --region $REGION \
  --query 'Configuration.FunctionName' \
  --output text

echo -e "${GREEN}"
echo "========== DEPLOYMENT COMPLETE =========="
echo "Lambda function: ingest-api-data"
echo "Region: $REGION"
echo ""
echo "Test it:"
echo "aws lambda invoke --function-name ingest-api-data response.json --region $REGION"
echo "cat response.json"
echo "=========================================="
echo -e "${NC}"

cd ..
