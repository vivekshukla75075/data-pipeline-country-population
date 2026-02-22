#!/bin/bash

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}========== Deploying New Architecture ==========${NC}"

AWS_REGION="us-east-1"
BUCKET_NAME="data-pipeline-country-population"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "AWS Region: $AWS_REGION"
echo "Account ID: $ACCOUNT_ID"
echo "Bucket: $BUCKET_NAME"

# Step 1: Upload scripts to S3
echo -e "${YELLOW}[1/5] Uploading scripts to S3...${NC}"
aws s3 cp Validation/validate_schema.py s3://$BUCKET_NAME/scripts/validate_schema.py
aws s3 cp Transformation/transform_data.py s3://$BUCKET_NAME/scripts/transform_data.py
echo -e "${GREEN}✓ Scripts uploaded${NC}"

# Step 2: Create Lambda function
echo -e "${YELLOW}[2/5] Creating Lambda function...${NC}"
cd lambda_deployment
zip -q ingest_api_data.zip ingest_api_data.py
cd ..

aws lambda create-function \
  --function-name ingest-api-data \
  --runtime python3.9 \
  --role arn:aws:iam::$ACCOUNT_ID:role/lambda-execution-role \
  --handler ingest_api_data.lambda_handler \
  --zip-file fileb://lambda_deployment/ingest_api_data.zip \
  --timeout 60 \
  --memory-size 256 \
  --region $AWS_REGION 2>/dev/null && echo -e "${GREEN}✓ Lambda function created${NC}" || echo -e "${YELLOW}⚠️ Lambda function may already exist${NC}"

# Step 3: Update Glue Validation Job
echo -e "${YELLOW}[3/5] Updating Glue Validation Job...${NC}"
aws glue update-job \
  --job-name country-population-validation \
  --job-command Name=glueetl,ScriptLocation=s3://$BUCKET_NAME/scripts/validate_schema.py \
  --role arn:aws:iam::$ACCOUNT_ID:role/glue-validation-role \
  --glue-version "3.0" \
  --worker-type G.1X \
  --number-of-workers 3 \
  --region $AWS_REGION 2>/dev/null && echo -e "${GREEN}✓ Validation job updated${NC}" || echo -e "${YELLOW}⚠️ Could not update validation job${NC}"

# Step 4: Update Glue Transformation Job
echo -e "${YELLOW}[4/5] Updating Glue Transformation Job...${NC}"
aws glue update-job \
  --job-name country-population-transformation \
  --job-command Name=glueetl,ScriptLocation=s3://$BUCKET_NAME/scripts/transform_data.py \
  --role arn:aws:iam::$ACCOUNT_ID:role/glue-validation-role \
  --glue-version "3.0" \
  --worker-type G.1X \
  --number-of-workers 5 \
  --region $AWS_REGION 2>/dev/null && echo -e "${GREEN}✓ Transformation job updated${NC}" || echo -e "${YELLOW}⚠️ Could not update transformation job${NC}"

# Step 5: Verify deployment
echo -e "${YELLOW}[5/5] Verifying deployment...${NC}"
echo "Lambda functions:"
aws lambda list-functions --region $AWS_REGION --query 'Functions[?contains(FunctionName, `ingest`)].FunctionName' --output text

echo "Glue jobs:"
aws glue list-jobs --region $AWS_REGION --query 'JobList[].Name' --output text

echo -e "${GREEN}"
echo "========== Deployment Complete =========="
echo ""
echo "Next Steps:"
echo "1. Test Lambda function:"
echo "   aws lambda invoke --function-name ingest-api-data response.json --region $AWS_REGION"
echo ""
echo "2. Run Glue Validation job (after Lambda completes):"
echo "   aws glue start-job-run --job-name country-population-validation --region $AWS_REGION"
echo ""
echo "3. Run Glue Transformation job (after Validation completes):"
echo "   aws glue start-job-run --job-name country-population-transformation --region $AWS_REGION"
echo ""
echo "4. Query results in Athena:"
echo "   SELECT region, COUNT(*) FROM country_population.countries_curated GROUP BY region"
echo "=========================================="
echo -e "${NC}"
