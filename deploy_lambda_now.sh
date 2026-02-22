#!/bin/bash

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}╔════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║   DEPLOY LAMBDA & VERIFY INGESTION LOGS        ║${NC}"
echo -e "${YELLOW}╚════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================================
# STEP 1: BUILD LAMBDA ZIP
# ============================================================================
echo -e "${YELLOW}[STEP 1] Building Lambda ZIP package...${NC}"

cd lambda_deployment

# Remove old ZIP
rm -f ingest_api_data.zip

# Verify Python file exists
if [ ! -f "ingest_api_data.py" ]; then
	echo -e "${RED}✗ ingest_api_data.py not found!${NC}"
	exit 1
fi

# Create new ZIP
zip -q ingest_api_data.zip ingest_api_data.py

if [ ! -f "ingest_api_data.zip" ]; then
	echo -e "${RED}✗ Failed to create ZIP${NC}"
	exit 1
fi

FILE_SIZE=$(ls -lh ingest_api_data.zip | awk '{print $5}')
echo -e "${GREEN}✓ Lambda ZIP created (${FILE_SIZE})${NC}"

cd ..
echo ""

# ============================================================================
# STEP 2: VERIFY LOG PATH IN CODE
# ============================================================================
echo -e "${YELLOW}[STEP 2] Verifying log path in Lambda code...${NC}"

if grep -q 'logs/ingestion_logs/' lambda_deployment/ingest_api_data.py; then
	echo -e "${GREEN}✓ Correct log path found: logs/ingestion_logs/${NC}"
else
	echo -e "${RED}✗ Log path not found in code${NC}"
	exit 1
fi

echo ""

# ============================================================================
# STEP 3: DEPLOY LAMBDA FUNCTION
# ============================================================================
echo -e "${YELLOW}[STEP 3] Deploying Lambda function...${NC}"

aws lambda update-function-code \
	--function-name ingest-api-data \
	--zip-file fileb://lambda_deployment/ingest_api_data.zip \
	--region us-east-1

echo -e "${GREEN}✓ Lambda function deployed${NC}"
echo ""

# ============================================================================
# STEP 4: TEST LAMBDA
# ============================================================================
echo -e "${YELLOW}[STEP 4] Testing Lambda execution...${NC}"

aws lambda invoke \
	--function-name ingest-api-data \
	--region us-east-1 \
	/tmp/response.json

RESPONSE=$(cat /tmp/response.json)
STATUS=$(echo "$RESPONSE" | jq -r '.statusCode')
RECORDS=$(echo "$RESPONSE" | jq -r '.body' | jq -r '.records')
API_STATUS=$(echo "$RESPONSE" | jq -r '.body' | jq -r '.api_status')

echo "Response:"
echo "$RESPONSE" | jq '.'

if [ "$STATUS" = "200" ]; then
	echo -e "${GREEN}✓ Lambda execution successful${NC}"
	echo "  Records: $RECORDS"
	echo "  API Status: $API_STATUS"
else
	echo -e "${RED}✗ Lambda execution failed${NC}"
	exit 1
fi

echo ""

# ============================================================================
# STEP 5: WAIT FOR S3 UPDATES
# ============================================================================
echo -e "${YELLOW}[STEP 5] Waiting 30 seconds for S3 updates...${NC}"
sleep 30
echo -e "${GREEN}✓ Done${NC}"
echo ""

# ============================================================================
# STEP 6: VERIFY LOGS FOLDER CREATED
# ============================================================================
echo -e "${YELLOW}[STEP 6] Checking logs folder structure...${NC}"

echo "S3 folders in logs/:"
aws s3 ls s3://data-pipeline-country-population/logs/ --region us-east-1

INGESTION_LOGS=$(aws s3 ls s3://data-pipeline-country-population/logs/ingestion_logs/ --region us-east-1 --recursive 2>/dev/null | wc -l)

if [ $INGESTION_LOGS -gt 0 ]; then
	echo -e "${GREEN}✓ ingestion_logs folder found${NC}"
	echo ""
	echo "Content of logs/ingestion_logs/:"
	aws s3 ls s3://data-pipeline-country-population/logs/ingestion_logs/ --region us-east-1 --recursive
else
	echo -e "${RED}✗ ingestion_logs folder NOT found${NC}"
	exit 1
fi

echo ""

# ============================================================================
# STEP 7: VERIFY RAW DATA
# ============================================================================
echo -e "${YELLOW}[STEP 7] Checking raw data folder...${NC}"

RAW_DATA=$(aws s3 ls s3://data-pipeline-country-population/raw/countries/ --region us-east-1 --recursive 2>/dev/null | wc -l)

if [ $RAW_DATA -gt 0 ]; then
	echo -e "${GREEN}✓ Raw data found${NC}"
	echo ""
	echo "Content of raw/countries/:"
	aws s3 ls s3://data-pipeline-country-population/raw/countries/ --region us-east-1 --recursive
else
	echo -e "${RED}✗ No raw data found${NC}"
	exit 1
fi

echo ""

# ============================================================================
# FINAL SUMMARY
# ============================================================================
echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         DEPLOYMENT SUCCESSFUL ✅               ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo ""

echo "Summary:"
echo "  ✅ Lambda ZIP built"
echo "  ✅ Lambda deployed"
echo "  ✅ Lambda tested"
echo "  ✅ Ingestion logs created in: logs/ingestion_logs/"
echo "  ✅ Raw data created in: raw/countries/"
echo ""

echo "Next steps:"
echo "  1. Run validation job:"
echo "     aws glue start-job-run --job-name country-population-validation --region us-east-1"
echo ""
echo "  2. Run transformation job (after validation completes):"
echo "     aws glue start-job-run --job-name country-population-transformation --region us-east-1"
echo ""

echo -e "${GREEN}✅ Pipeline ready!${NC}"
