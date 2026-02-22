#!/bin/bash

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║         SETUP GLUE JOBS WITH CORRECT SCRIPTS          ║${NC}"
echo -e "${YELLOW}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"
BUCKET="data-pipeline-country-population"

echo "Configuration:"
echo "  Account ID: $ACCOUNT_ID"
echo "  Region: $REGION"
echo "  Bucket: $BUCKET"
echo ""

# ============================================================================
# STEP 1: VERIFY SCRIPTS IN S3
# ============================================================================
echo -e "${YELLOW}[STEP 1] Verifying scripts in S3...${NC}"

echo "Checking validation script..."
aws s3 ls s3://$BUCKET/scripts/validate_schema.py --region $REGION && echo -e "${GREEN}✓ Found${NC}" || echo -e "${RED}✗ Not found${NC}"

echo "Checking transformation script..."
aws s3 ls s3://$BUCKET/scripts/transform_data.py --region $REGION && echo -e "${GREEN}✓ Found${NC}" || echo -e "${RED}✗ Not found${NC}"

echo ""

# ============================================================================
# STEP 2: DELETE OLD JOBS
# ============================================================================
echo -e "${YELLOW}[STEP 2] Removing old Glue jobs...${NC}"

aws glue delete-job --job-name country-population-validation --region $REGION 2>/dev/null || echo "Validation job doesn't exist"
echo -e "${GREEN}✓ Validation job removed${NC}"

aws glue delete-job --job-name country-population-transformation --region $REGION 2>/dev/null || echo "Transformation job doesn't exist"
echo -e "${GREEN}✓ Transformation job removed${NC}"

echo ""

# ============================================================================
# STEP 3: CREATE VALIDATION JOB
# ============================================================================
echo -e "${YELLOW}[STEP 3] Creating Validation job...${NC}"

aws glue create-job \
  --name country-population-validation \
  --role arn:aws:iam::${ACCOUNT_ID}:role/glue-validation-role \
  --command Name=glueetl,ScriptLocation=s3://${BUCKET}/scripts/validate_schema.py \
  --glue-version 3.0 \
  --worker-type G.1X \
  --number-of-workers 3 \
  --timeout 60 \
  --region $REGION

echo -e "${GREEN}✓ Validation job created${NC}"
echo ""

# ============================================================================
# STEP 4: CREATE TRANSFORMATION JOB
# ============================================================================
echo -e "${YELLOW}[STEP 4] Creating Transformation job...${NC}"

aws glue create-job \
  --name country-population-transformation \
  --role arn:aws:iam::${ACCOUNT_ID}:role/glue-validation-role \
  --command Name=glueetl,ScriptLocation=s3://${BUCKET}/scripts/transform_data.py \
  --glue-version 3.0 \
  --worker-type G.1X \
  --number-of-workers 5 \
  --timeout 60 \
  --region $REGION

echo -e "${GREEN}✓ Transformation job created${NC}"
echo ""

# ============================================================================
# STEP 5: VERIFY JOBS
# ============================================================================
echo -e "${YELLOW}[STEP 5] Verifying Glue jobs...${NC}"

echo "Validation job:"
aws glue get-job --job-name country-population-validation --region $REGION --query 'Job.Command.ScriptLocation' --output text

echo ""
echo "Transformation job:"
aws glue get-job --job-name country-population-transformation --region $REGION --query 'Job.Command.ScriptLocation' --output text

echo ""

# ============================================================================
# FINAL SUMMARY
# ============================================================================
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           GLUE JOBS SETUP COMPLETE ✅                 ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

echo "Summary:"
echo "  ✅ Validation job: country-population-validation"
echo "  ✅ Transformation job: country-population-transformation"
echo ""

echo "Next steps:"
echo "  1. Run Lambda ingestion:"
echo "     aws lambda invoke --function-name ingest-api-data response.json --region $REGION"
echo ""
echo "  2. Run Validation job:"
echo "     aws glue start-job-run --job-name country-population-validation --region $REGION"
echo ""
echo "  3. Run Transformation job:"
echo "     aws glue start-job-run --job-name country-population-transformation --region $REGION"
echo ""

echo -e "${GREEN}✅ Glue jobs are ready!${NC}"
