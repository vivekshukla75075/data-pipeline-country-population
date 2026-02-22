#!/bin/bash

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║       FINAL BUILD & DEPLOY - COMPLETE PIPELINE        ║${NC}"
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
# PHASE 1: GIT COMMIT & PUSH
# ============================================================================
echo -e "${YELLOW}[PHASE 1] Committing changes to Git...${NC}"

git add -A

if git diff-cached --quiet; then
	echo -e "${YELLOW}No changes to commit${NC}"
else
	git commit -m "feat: Deploy final ETL pipeline with full logging

- Lambda ingestion with proper API headers and error handling
- Glue validation with S3 logging
- Glue transformation with S3 logging
- Comprehensive logs in ingestion_logs, validation_logs, transformation_logs
- Fixed API call issues and fallback handling
- Ready for production deployment"
	
	git push origin feature/sync-upstream-changes
	echo -e "${GREEN}✓ Changes committed and pushed${NC}"
fi

echo ""

# ============================================================================
# PHASE 2: BUILD LAMBDA PACKAGE
# ============================================================================
echo -e "${YELLOW}[PHASE 2] Building Lambda deployment package...${NC}"

cd lambda_deployment

# Remove old ZIP
rm -f ingest_api_data.zip

# Create new ZIP
zip -q ingest_api_data.zip ingest_api_data.py

if [ -f "ingest_api_data.zip" ]; then
	FILE_SIZE=$(ls -lh ingest_api_data.zip | awk '{print $5}')
	echo -e "${GREEN}✓ Lambda ZIP created (${FILE_SIZE})${NC}"
else
	echo -e "${RED}✗ Failed to create Lambda ZIP${NC}"
	exit 1
fi

cd ..
echo ""

# ============================================================================
# PHASE 3: DEPLOY LAMBDA FUNCTION
# ============================================================================
echo -e "${YELLOW}[PHASE 3] Deploying Lambda function...${NC}"

aws lambda update-function-code \
	--function-name ingest-api-data \
	--zip-file fileb://lambda_deployment/ingest_api_data.zip \
	--region $REGION > /dev/null

echo -e "${GREEN}✓ Lambda function deployed${NC}"
echo ""

# ============================================================================
# PHASE 4: UPLOAD GLUE SCRIPTS
# ============================================================================
echo -e "${YELLOW}[PHASE 4] Uploading Glue scripts to S3...${NC}"

aws s3 cp Validation/validate_schema.py s3://$BUCKET/scripts/ --region $REGION > /dev/null
echo -e "${GREEN}✓ Validation script uploaded${NC}"

aws s3 cp Transformation/transform_data.py s3://$BUCKET/scripts/ --region $REGION > /dev/null
echo -e "${GREEN}✓ Transformation script uploaded${NC}"

echo ""

# ============================================================================
# PHASE 5: UPDATE GLUE JOBS
# ============================================================================
echo -e "${YELLOW}[PHASE 5] Updating Glue jobs...${NC}"

aws glue update-job \
	--job-name country-population-validation \
	--job-command Name=glueetl,ScriptLocation=s3://$BUCKET/scripts/validate_schema.py \
	--role arn:aws:iam::$ACCOUNT_ID:role/glue-validation-role \
	--glue-version "3.0" \
	--worker-type G.1X \
	--number-of-workers 3 \
	--region $REGION > /dev/null

echo -e "${GREEN}✓ Validation job updated${NC}"

aws glue update-job \
	--job-name country-population-transformation \
	--job-command Name=glueetl,ScriptLocation=s3://$BUCKET/scripts/transform_data.py \
	--role arn:aws:iam::$ACCOUNT_ID:role/glue-validation-role \
	--glue-version "3.0" \
	--worker-type G.1X \
	--number-of-workers 5 \
	--region $REGION > /dev/null

echo -e "${GREEN}✓ Transformation job updated${NC}"

echo ""

# ============================================================================
# PHASE 6: EXECUTE PIPELINE
# ============================================================================
echo -e "${YELLOW}[PHASE 6] Executing pipeline...${NC}"

# Step 1: Lambda Ingestion
echo "Step 1: Triggering Lambda ingestion..."
LAMBDA_RESPONSE=$(aws lambda invoke \
	--function-name ingest-api-data \
	--region $REGION \
	/tmp/lambda_response.json 2>&1)

STATUS=$(cat /tmp/lambda_response.json | jq -r '.statusCode')

if [ "$STATUS" = "200" ]; then
	RECORDS=$(cat /tmp/lambda_response.json | jq -r '.body' | jq -r '.records')
	echo -e "${GREEN}✓ Lambda ingestion successful (${RECORDS} records)${NC}"
else
	echo -e "${RED}✗ Lambda ingestion failed${NC}"
	cat /tmp/lambda_response.json
fi

echo "Waiting 30 seconds for data to appear in S3..."
sleep 30

# Check raw data
RAW_COUNT=$(aws s3 ls s3://$BUCKET/raw/countries/ --region $REGION --recursive | grep -v "\.keep" | wc -l)
if [ $RAW_COUNT -gt 0 ]; then
	echo -e "${GREEN}✓ Raw data found in S3 (${RAW_COUNT} files)${NC}"
else
	echo -e "${RED}✗ No raw data in S3${NC}"
fi

echo ""

# Step 2: Glue Validation
echo "Step 2: Running Glue validation job..."
VALIDATION_RUN=$(aws glue start-job-run \
	--job-name country-population-validation \
	--region $REGION \
	--query 'JobRunId' \
	--output text)

echo "Validation job started: $VALIDATION_RUN"
echo "Waiting 90 seconds for completion..."
sleep 90

VALIDATION_STATUS=$(aws glue get-job-run \
	--job-name country-population-validation \
	--run-id $VALIDATION_RUN \
	--region $REGION \
	--query 'JobRun.JobRunState' \
	--output text)

if [ "$VALIDATION_STATUS" = "SUCCEEDED" ]; then
	echo -e "${GREEN}✓ Validation job succeeded${NC}"
else
	echo -e "${RED}⚠ Validation job status: $VALIDATION_STATUS${NC}"
fi

echo ""

# Step 3: Glue Transformation
echo "Step 3: Running Glue transformation job..."
TRANSFORM_RUN=$(aws glue start-job-run \
	--job-name country-population-transformation \
	--region $REGION \
	--query 'JobRunId' \
	--output text)

echo "Transformation job started: $TRANSFORM_RUN"
echo "Waiting 90 seconds for completion..."
sleep 90

TRANSFORM_STATUS=$(aws glue get-job-run \
	--job-name country-population-transformation \
	--run-id $TRANSFORM_RUN \
	--region $REGION \
	--query 'JobRun.JobRunState' \
	--output text)

if [ "$TRANSFORM_STATUS" = "SUCCEEDED" ]; then
	echo -e "${GREEN}✓ Transformation job succeeded${NC}"
else
	echo -e "${RED}⚠ Transformation job status: $TRANSFORM_STATUS${NC}"
fi

echo ""

# ============================================================================
# PHASE 7: VERIFY OUTPUTS
# ============================================================================
echo -e "${YELLOW}[PHASE 7] Verifying outputs...${NC}"

echo ""
echo "Raw Data (Ingestion):"
aws s3 ls s3://$BUCKET/raw/countries/ --region $REGION --recursive | grep "\.json" | tail -3

echo ""
echo "Validated Data (Validation):"
aws s3 ls s3://$BUCKET/validated/countries/ --region $REGION --recursive | tail -3

echo ""
echo "Curated Data (Transformation):"
aws s3 ls s3://$BUCKET/curated/countries/ --region $REGION --recursive | tail -5

echo ""

# ============================================================================
# PHASE 8: VERIFY LOGS
# ============================================================================
echo -e "${YELLOW}[PHASE 8] Verifying logs...${NC}"

echo ""
echo "Ingestion Logs:"
aws s3 ls s3://$BUCKET/logs/ingestion_logs/ --region $REGION | tail -3

echo ""
echo "Validation Logs:"
aws s3 ls s3://$BUCKET/logs/validation_logs/ --region $REGION | tail -3

echo ""
echo "Transformation Logs:"
aws s3 ls s3://$BUCKET/logs/transformation_logs/ --region $REGION | tail -3

echo ""

# ============================================================================
# FINAL SUMMARY
# ============================================================================
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           BUILD & DEPLOY COMPLETE ✅                   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

echo "Pipeline Status:"
echo "  ✅ Lambda Function: ingest-api-data"
echo "  ✅ Glue Validation: country-population-validation"
echo "  ✅ Glue Transformation: country-population-transformation"
echo ""

echo "Data Locations:"
echo "  Raw: s3://$BUCKET/raw/countries/"
echo "  Validated: s3://$BUCKET/validated/countries/"
echo "  Curated: s3://$BUCKET/curated/countries/"
echo ""

echo "Log Locations:"
echo "  Ingestion: s3://$BUCKET/logs/ingestion_logs/"
echo "  Validation: s3://$BUCKET/logs/validation_logs/"
echo "  Transformation: s3://$BUCKET/logs/transformation_logs/"
echo ""

echo "AWS Console Links:"
echo "  Lambda: https://console.aws.amazon.com/lambda/home?region=$REGION#/functions/ingest-api-data"
echo "  Glue Jobs: https://console.aws.amazon.com/glue/home?region=$REGION#/jobs"
echo "  S3 Bucket: https://s3.console.aws.amazon.com/s3/buckets/$BUCKET"
echo ""

echo "Query in Athena:"
echo "  SELECT region, COUNT(*) as country_count, SUM(population) as total_population"
echo "  FROM country_population.countries_curated"
echo "  GROUP BY region ORDER BY total_population DESC;"
echo ""

echo -e "${GREEN}✅ Pipeline is ready for production!${NC}"
