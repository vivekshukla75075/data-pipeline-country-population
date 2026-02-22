#!/bin/bash

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}"
echo "========== COMPLETE PIPELINE DEPLOYMENT =========="
echo -e "${NC}"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"
BUCKET="data-pipeline-country-population"

echo "Account: $ACCOUNT_ID"
echo "Region: $REGION"
echo "Bucket: $BUCKET"
echo ""

# Step 1: Deploy Lambda
echo -e "${YELLOW}[1/3] Deploying Lambda Ingestion Function...${NC}"
chmod +x deploy_lambda.sh
./deploy_lambda.sh

# Step 2: Upload Glue Scripts
echo -e "${YELLOW}[2/3] Uploading Glue Scripts to S3...${NC}"
aws s3 cp Validation/validate_schema.py s3://$BUCKET/scripts/ --region $REGION
aws s3 cp Transformation/transform_data.py s3://$BUCKET/scripts/ --region $REGION
echo -e "${GREEN}✓ Glue scripts uploaded${NC}"

# Step 3: Update Glue Jobs
echo -e "${YELLOW}[3/3] Updating Glue Jobs...${NC}"

aws glue update-job \
  --job-name country-population-validation \
  --job-command Name=glueetl,ScriptLocation=s3://$BUCKET/scripts/validate_schema.py \
  --role arn:aws:iam::$ACCOUNT_ID:role/glue-validation-role \
  --glue-version "3.0" \
  --worker-type G.1X \
  --number-of-workers 3 \
  --region $REGION 2>/dev/null && echo -e "${GREEN}✓ Validation job updated${NC}"

aws glue update-job \
  --job-name country-population-transformation \
  --job-command Name=glueetl,ScriptLocation=s3://$BUCKET/scripts/transform_data.py \
  --role arn:aws:iam::$ACCOUNT_ID:role/glue-validation-role \
  --glue-version "3.0" \
  --worker-type G.1X \
  --number-of-workers 5 \
  --region $REGION 2>/dev/null && echo -e "${GREEN}✓ Transformation job updated${NC}"

echo -e "${GREEN}"
echo "========== DEPLOYMENT COMPLETE =========="
echo ""
echo "Pipeline ready! Execute with:"
echo ""
echo "1. Trigger Lambda (API Ingestion):"
echo "   aws lambda invoke --function-name ingest-api-data response.json --region $REGION"
echo ""
echo "2. Run Validation (after 30 seconds):"
echo "   aws glue start-job-run --job-name country-population-validation --region $REGION"
echo ""
echo "3. Run Transformation (after validation completes):"
echo "   aws glue start-job-run --job-name country-population-transformation --region $REGION"
echo ""
echo "4. Query results in Athena:"
echo "   SELECT region, COUNT(*) FROM country_population.countries_curated GROUP BY region"
echo ""
echo "=========================================="
echo -e "${NC}"
