#!/bin/bash

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║         DEPLOY & VERIFY ETL PIPELINE                  ║${NC}"
echo -e "${YELLOW}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"
BUCKET="data-pipeline-country-population"

# ============================================================================
# STEP 1: RECREATE LAMBDA ZIP
# ============================================================================
echo -e "${YELLOW}[STEP 1] Recreating Lambda deployment package...${NC}"

cd lambda_deployment

# Remove old ZIP
rm -f ingest_api_data.zip

# Create new ZIP with updated code
zip -q ingest_api_data.zip ingest_api_data.py

if [ -f "ingest_api_data.zip" ]; then
	echo -e "${GREEN}✓ Lambda ZIP created successfully${NC}"
	ls -lh ingest_api_data.zip
else
	echo -e "${RED}✗ Failed to create Lambda ZIP${NC}"
	exit 1
fi

cd ..
echo ""

# ============================================================================
# STEP 2: UPDATE LAMBDA FUNCTION
# ============================================================================
echo -e "${YELLOW}[STEP 2] Updating Lambda function...${NC}"

aws lambda update-function-code \
	--function-name ingest-api-data \
	--zip-file fileb://lambda_deployment/ingest_api_data.zip \
	--region $REGION

echo -e "${GREEN}✓ Lambda function updated${NC}"
echo ""

# ============================================================================
# STEP 3: UPLOAD GLUE SCRIPTS
# ============================================================================
echo -e "${YELLOW}[STEP 3] Uploading Glue scripts...${NC}"

aws s3 cp Validation/validate_schema.py s3://$BUCKET/scripts/ --region $REGION
aws s3 cp Transformation/transform_data.py s3://$BUCKET/scripts/ --region $REGION

echo -e "${GREEN}✓ Glue scripts uploaded${NC}"
echo ""

# ============================================================================
# STEP 4: TEST LAMBDA INGESTION
# ============================================================================
echo -e "${YELLOW}[STEP 4] Testing Lambda ingestion...${NC}"

aws lambda invoke \
	--function-name ingest-api-data \
	--region $REGION \
	/tmp/lambda_response.json

RESPONSE=$(cat /tmp/lambda_response.json)
echo "Lambda Response:"
echo "$RESPONSE" | jq '.'

STATUS=$(echo "$RESPONSE" | jq -r '.statusCode')

if [ "$STATUS" = "200" ]; then
	echo -e "${GREEN}✓ Lambda execution successful${NC}"
	RECORDS=$(echo "$RESPONSE" | jq -r '.body' | jq -r '.records')
	echo "  Records fetched: $RECORDS"
else
	echo -e "${RED}✗ Lambda execution failed${NC}"
	echo "$RESPONSE"
fi

echo ""

# ============================================================================
# STEP 5: CHECK S3 INGESTION OUTPUT
# ============================================================================
echo -e "${YELLOW}[STEP 5] Checking S3 raw folder...${NC}"

RAW_FILES=$(aws s3 ls s3://$BUCKET/raw/countries/ --region $REGION --recursive)

if [ -z "$RAW_FILES" ]; then
	echo -e "${RED}✗ No files in raw folder${NC}"
else
	echo -e "${GREEN}✓ Raw files found:${NC}"
	echo "$RAW_FILES"
fi

echo ""

# ============================================================================
# STEP 6: CHECK INGESTION LOGS
# ============================================================================
echo -e "${YELLOW}[STEP 6] Checking ingestion logs...${NC}"

INGESTION_LOGS=$(aws s3 ls s3://$BUCKET/logs/ingestion_logs/ --region $REGION --recursive 2>/dev/null)

if [ -z "$INGESTION_LOGS" ]; then
	echo -e "${RED}✗ No ingestion logs found${NC}"
else
	echo -e "${GREEN}✓ Ingestion logs found:${NC}"
	echo "$INGESTION_LOGS"
	
	# Get latest log
	LATEST_LOG=$(echo "$INGESTION_LOGS" | tail -1 | awk '{print $NF}')
	echo ""
	echo "Latest log content:"
	aws s3 cp s3://$BUCKET/$LATEST_LOG - --region $REGION | head -30
fi

echo ""

# ============================================================================
# STEP 7: RUN VALIDATION JOB
# ============================================================================
echo -e "${YELLOW}[STEP 7] Running Glue Validation job...${NC}"

VALIDATION_RUN=$(aws glue start-job-run \
	--job-name country-population-validation \
	--region $REGION \
	--query 'JobRunId' \
	--output text)

echo "Validation job started: $VALIDATION_RUN"
echo "Waiting 90 seconds for completion..."
sleep 90

# Check validation status
VALIDATION_STATUS=$(aws glue get-job-run \
	--job-name country-population-validation \
	--run-id $VALIDATION_RUN \
	--region $REGION \
	--query 'JobRun.JobRunState' \
	--output text)

echo "Validation job status: $VALIDATION_STATUS"

if [ "$VALIDATION_STATUS" = "SUCCEEDED" ]; then
	echo -e "${GREEN}✓ Validation job succeeded${NC}"
else
	echo -e "${RED}✗ Validation job status: $VALIDATION_STATUS${NC}"
fi

echo ""

# ============================================================================
# STEP 8: CHECK VALIDATED OUTPUT
# ============================================================================
echo -e "${YELLOW}[STEP 8] Checking validated folder...${NC}"

VALIDATED_FILES=$(aws s3 ls s3://$BUCKET/validated/countries/ --region $REGION --recursive 2>/dev/null)

if [ -z "$VALIDATED_FILES" ]; then
	echo -e "${RED}✗ No files in validated folder${NC}"
	echo "  Possible reasons:"
	echo "  1. Validation job failed"
	echo "  2. No raw data to validate"
	echo "  3. Validation logic filtering all records"
else
	echo -e "${GREEN}✓ Validated files found:${NC}"
	echo "$VALIDATED_FILES"
fi

echo ""

# ============================================================================
# STEP 9: CHECK VALIDATION LOGS
# ============================================================================
echo -e "${YELLOW}[STEP 9] Checking validation logs...${NC}"

VALIDATION_LOGS=$(aws s3 ls s3://$BUCKET/logs/validation_logs/ --region $REGION --recursive 2>/dev/null)

if [ -z "$VALIDATION_LOGS" ]; then
	echo -e "${RED}✗ No validation logs found${NC}"
else
	echo -e "${GREEN}✓ Validation logs found:${NC}"
	echo "$VALIDATION_LOGS"
	
	# Get latest log
	LATEST_VALIDATION_LOG=$(echo "$VALIDATION_LOGS" | tail -1 | awk '{print $NF}')
	echo ""
	echo "Latest validation log content:"
	aws s3 cp s3://$BUCKET/$LATEST_VALIDATION_LOG - --region $REGION | head -40
fi

echo ""

# ============================================================================
# FINAL SUMMARY
# ============================================================================
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              VERIFICATION COMPLETE                    ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

echo "Pipeline Status:"
echo "  Lambda Ingestion: $([ -n "$RAW_FILES" ] && echo '✅' || echo '❌')"
echo "  Validation Job: $([ "$VALIDATION_STATUS" = "SUCCEEDED" ] && echo '✅' || echo '❌')"
echo "  Validated Data: $([ -n "$VALIDATED_FILES" ] && echo '✅' || echo '❌')"
echo ""

echo "Log Locations:"
echo "  Ingestion: s3://$BUCKET/logs/ingestion_logs/"
echo "  Validation: s3://$BUCKET/logs/validation_logs/"
echo "  Transformation: s3://$BUCKET/logs/transformation_logs/"
echo ""

if [ -n "$RAW_FILES" ] && [ "$VALIDATION_STATUS" = "SUCCEEDED" ] && [ -n "$VALIDATED_FILES" ]; then
	echo -e "${GREEN}✅ Pipeline is working correctly!${NC}"
else
	echo -e "${RED}⚠️ Pipeline has issues. Check logs above.${NC}"
fi
