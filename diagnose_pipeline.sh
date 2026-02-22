#!/bin/bash

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}========== PIPELINE DIAGNOSTICS ==========${NC}"
echo ""

BUCKET="data-pipeline-country-population"
REGION="us-east-1"

# Check 1: Raw files
echo -e "${YELLOW}1. Raw Files in S3:${NC}"
RAW_FILES=$(aws s3 ls s3://$BUCKET/raw/countries/ --region $REGION --recursive)
if [ -n "$RAW_FILES" ]; then
	echo -e "${GREEN}✓ Found:${NC}"
	echo "$RAW_FILES"
	FILE_COUNT=$(echo "$RAW_FILES" | wc -l)
	echo "Total files: $FILE_COUNT"
else
	echo -e "${RED}✗ No raw files found${NC}"
fi
echo ""

# Check 2: Validated files
echo -e "${YELLOW}2. Validated Files in S3:${NC}"
VALIDATED_FILES=$(aws s3 ls s3://$BUCKET/validated/countries/ --region $REGION --recursive)
if [ -n "$VALIDATED_FILES" ]; then
	echo -e "${GREEN}✓ Found:${NC}"
	echo "$VALIDATED_FILES"
else
	echo -e "${RED}✗ No validated files found${NC}"
fi
echo ""

# Check 3: Lambda logs
echo -e "${YELLOW}3. Lambda Function Logs:${NC}"
LATEST_LAMBDA_LOG=$(aws logs describe-log-streams \
	--log-group-name /aws/lambda/ingest-api-data \
	--region $REGION \
	--order-by LastEventTime \
	--descending \
	--query 'logStreams[0].logStreamName' \
	--output text 2>/dev/null)

if [ -n "$LATEST_LAMBDA_LOG" ] && [ "$LATEST_LAMBDA_LOG" != "None" ]; then
	echo -e "${GREEN}✓ Lambda logs found:${NC}"
	aws logs get-log-events \
		--log-group-name /aws/lambda/ingest-api-data \
		--log-stream-name "$LATEST_LAMBDA_LOG" \
		--region $REGION \
		--query 'events[].message' \
		--output text | tail -20
else
	echo -e "${RED}✗ No Lambda logs found${NC}"
fi
echo ""

# Check 4: Glue job logs
echo -e "${YELLOW}4. Glue Validation Job Logs:${NC}"
LATEST_GLUE_LOG=$(aws logs describe-log-streams \
	--log-group-name /aws-glue/jobs/country-population-validation \
	--region $REGION \
	--order-by LastEventTime \
	--descending \
	--query 'logStreams[0].logStreamName' \
	--output text 2>/dev/null)

if [ -n "$LATEST_GLUE_LOG" ] && [ "$LATEST_GLUE_LOG" != "None" ]; then
	echo -e "${GREEN}✓ Glue logs found:${NC}"
	aws logs get-log-events \
		--log-group-name /aws-glue/jobs/country-population-validation \
		--log-stream-name "$LATEST_GLUE_LOG" \
		--region $REGION \
		--query 'events[].message' \
		--output text | tail -30
else
	echo -e "${RED}✗ No Glue logs found${NC}"
fi
echo ""

# Check 5: S3 bucket logs
echo -e "${YELLOW}5. S3 Ingestion Logs:${NC}"
INGEST_LOGS=$(aws s3 ls s3://$BUCKET/logs/ingestion_logs/ --region $REGION)
if [ -n "$INGEST_LOGS" ]; then
	echo -e "${GREEN}✓ Ingestion logs:${NC}"
	echo "$INGEST_LOGS"
else
	echo -e "${RED}✗ No ingestion logs in S3${NC}"
fi
echo ""

echo -e "${YELLOW}6. S3 Validation Logs:${NC}"
VALIDATION_LOGS=$(aws s3 ls s3://$BUCKET/logs/validation_logs/ --region $REGION)
if [ -n "$VALIDATION_LOGS" ]; then
	echo -e "${GREEN}✓ Validation logs:${NC}"
	echo "$VALIDATION_LOGS"
else
	echo -e "${RED}✗ No validation logs in S3${NC}"
fi
echo ""

echo -e "${YELLOW}Summary:${NC}"
echo "  Raw files: $([ -n "$RAW_FILES" ] && echo '✅' || echo '❌')"
echo "  Validated files: $([ -n "$VALIDATED_FILES" ] && echo '✅' || echo '❌')"
echo "  Lambda logs: $([ -n "$LATEST_LAMBDA_LOG" ] && [ "$LATEST_LAMBDA_LOG" != "None" ] && echo '✅' || echo '❌')"
echo "  Glue logs: $([ -n "$LATEST_GLUE_LOG" ] && [ "$LATEST_GLUE_LOG" != "None" ] && echo '✅' || echo '❌')"
