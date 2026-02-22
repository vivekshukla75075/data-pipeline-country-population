#!/bin/bash

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║         VERIFY COMPLETE DEPLOYMENT                    ║${NC}"
echo -e "${YELLOW}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

BUCKET="data-pipeline-country-population"
REGION="us-east-1"

# ============================================================================
# CHECK 1: LAMBDA FUNCTION
# ============================================================================
echo -e "${YELLOW}[CHECK 1] Verifying Lambda function...${NC}"

LAMBDA_EXISTS=$(aws lambda list-functions --region $REGION --query "Functions[?FunctionName=='ingest-api-data'].FunctionName" --output text 2>/dev/null)

if [ -n "$LAMBDA_EXISTS" ]; then
	echo -e "${GREEN}✓ Lambda function exists: ingest-api-data${NC}"
	
	# Get Lambda details
	LAMBDA_LAST_MODIFIED=$(aws lambda get-function --function-name ingest-api-data --region $REGION --query 'Configuration.LastModified' --output text 2>/dev/null)
	echo "  Last modified: $LAMBDA_LAST_MODIFIED"
	
	# Get Lambda code size
	LAMBDA_CODE_SIZE=$(aws lambda get-function --function-name ingest-api-data --region $REGION --query 'Configuration.CodeSize' --output text 2>/dev/null)
	echo "  Code size: $LAMBDA_CODE_SIZE bytes"
else
	echo -e "${RED}✗ Lambda function NOT found${NC}"
	exit 1
fi

echo ""

# ============================================================================
# CHECK 2: LAMBDA EXECUTION
# ============================================================================
echo -e "${YELLOW}[CHECK 2] Testing Lambda execution...${NC}"

aws lambda invoke \
	--function-name ingest-api-data \
	--region $REGION \
	/tmp/lambda_test.json > /dev/null 2>&1

STATUS=$(cat /tmp/lambda_test.json | jq -r '.statusCode')
RECORDS=$(cat /tmp/lambda_test.json | jq -r '.body' | jq -r '.records' 2>/dev/null || echo "0")

if [ "$STATUS" = "200" ]; then
	echo -e "${GREEN}✓ Lambda executed successfully${NC}"
	echo "  Status code: 200"
	echo "  Records fetched: $RECORDS"
else
	echo -e "${RED}✗ Lambda execution failed${NC}"
	echo "  Status code: $STATUS"
	cat /tmp/lambda_test.json | jq '.'
fi

echo ""

# ============================================================================
# CHECK 3: INGESTION LOGS
# ============================================================================
echo -e "${YELLOW}[CHECK 3] Verifying ingestion logs...${NC}"

INGESTION_LOGS=$(aws s3 ls s3://$BUCKET/logs/ingestion_logs/ --region $REGION --recursive 2>/dev/null | wc -l)

if [ $INGESTION_LOGS -gt 0 ]; then
	echo -e "${GREEN}✓ Ingestion logs found${NC}"
	echo "  Location: s3://$BUCKET/logs/ingestion_logs/"
	echo "  Files:"
	aws s3 ls s3://$BUCKET/logs/ingestion_logs/ --region $REGION | tail -5
else
	echo -e "${RED}✗ No ingestion logs found${NC}"
fi

echo ""

# ============================================================================
# CHECK 4: RAW DATA
# ============================================================================
echo -e "${YELLOW}[CHECK 4] Verifying raw data...${NC}"

RAW_DATA=$(aws s3 ls s3://$BUCKET/raw/countries/ --region $REGION --recursive 2>/dev/null | wc -l)

if [ $RAW_DATA -gt 0 ]; then
	echo -e "${GREEN}✓ Raw data files found${NC}"
	echo "  Location: s3://$BUCKET/raw/countries/"
	echo "  Files:"
	aws s3 ls s3://$BUCKET/raw/countries/ --region $REGION
else
	echo -e "${RED}✗ No raw data found${NC}"
fi

echo ""

# ============================================================================
# CHECK 5: GLUE VALIDATION JOB
# ============================================================================
echo -e "${YELLOW}[CHECK 5] Verifying Glue Validation job...${NC}"

VALIDATION_JOB=$(aws glue list-jobs --region $REGION --query "JobList[?Name=='country-population-validation'].Name" --output text 2>/dev/null)

if [ -n "$VALIDATION_JOB" ]; then
	echo -e "${GREEN}✓ Validation job exists: country-population-validation${NC}"
	
	# Get job details
	JOB_SCRIPT=$(aws glue get-job --job-name country-population-validation --region $REGION --query 'Job.Command.ScriptLocation' --output text 2>/dev/null)
	echo "  Script location: $JOB_SCRIPT"
else
	echo -e "${RED}✗ Validation job NOT found${NC}"
fi

echo ""

# ============================================================================
# CHECK 6: GLUE TRANSFORMATION JOB
# ============================================================================
echo -e "${YELLOW}[CHECK 6] Verifying Glue Transformation job...${NC}"

TRANSFORM_JOB=$(aws glue list-jobs --region $REGION --query "JobList[?Name=='country-population-transformation'].Name" --output text 2>/dev/null)

if [ -n "$TRANSFORM_JOB" ]; then
	echo -e "${GREEN}✓ Transformation job exists: country-population-transformation${NC}"
	
	# Get job details
	JOB_SCRIPT=$(aws glue get-job --job-name country-population-transformation --region $REGION --query 'Job.Command.ScriptLocation' --output text 2>/dev/null)
	echo "  Script location: $JOB_SCRIPT"
else
	echo -e "${RED}✗ Transformation job NOT found${NC}"
fi

echo ""

# ============================================================================
# CHECK 7: S3 SCRIPTS
# ============================================================================
echo -e "${YELLOW}[CHECK 7] Verifying uploaded scripts...${NC}"

VALIDATION_SCRIPT=$(aws s3 ls s3://$BUCKET/scripts/validate_schema.py --region $REGION 2>/dev/null)
TRANSFORM_SCRIPT=$(aws s3 ls s3://$BUCKET/scripts/transform_data.py --region $REGION 2>/dev/null)

if [ -n "$VALIDATION_SCRIPT" ] && [ -n "$TRANSFORM_SCRIPT" ]; then
	echo -e "${GREEN}✓ Both Glue scripts uploaded${NC}"
	echo "  Validation script: s3://$BUCKET/scripts/validate_schema.py"
	echo "  Transformation script: s3://$BUCKET/scripts/transform_data.py"
else
	echo -e "${RED}✗ Scripts missing in S3${NC}"
fi

echo ""

# ============================================================================
# CHECK 8: VALIDATION LOGS
# ============================================================================
echo -e "${YELLOW}[CHECK 8] Verifying validation logs...${NC}"

VALIDATION_LOGS=$(aws s3 ls s3://$BUCKET/logs/validation_logs/ --region $REGION --recursive 2>/dev/null | wc -l)

if [ $VALIDATION_LOGS -gt 0 ]; then
	echo -e "${GREEN}✓ Validation logs found${NC}"
	echo "  Location: s3://$BUCKET/logs/validation_logs/"
	echo "  Files:"
	aws s3 ls s3://$BUCKET/logs/validation_logs/ --region $REGION | tail -5
else
	echo -e "${YELLOW}⚠ No validation logs found (job may not have run yet)${NC}"
fi

echo ""

# ============================================================================
# CHECK 9: VALIDATED DATA
# ============================================================================
echo -e "${YELLOW}[CHECK 9] Verifying validated data...${NC}"

VALIDATED_DATA=$(aws s3 ls s3://$BUCKET/validated/countries/ --region $REGION --recursive 2>/dev/null | wc -l)

if [ $VALIDATED_DATA -gt 0 ]; then
	echo -e "${GREEN}✓ Validated data found${NC}"
	echo "  Location: s3://$BUCKET/validated/countries/"
	echo "  Files:"
	aws s3 ls s3://$BUCKET/validated/countries/ --region $REGION | tail -5
else
	echo -e "${YELLOW}⚠ No validated data found (validation job may not have run yet)${NC}"
fi

echo ""

# ============================================================================
# CHECK 10: TRANSFORMATION LOGS
# ============================================================================
echo -e "${YELLOW}[CHECK 10] Verifying transformation logs...${NC}"

TRANSFORM_LOGS=$(aws s3 ls s3://$BUCKET/logs/transformation_logs/ --region $REGION --recursive 2>/dev/null | wc -l)

if [ $TRANSFORM_LOGS -gt 0 ]; then
	echo -e "${GREEN}✓ Transformation logs found${NC}"
	echo "  Location: s3://$BUCKET/logs/transformation_logs/"
	echo "  Files:"
	aws s3 ls s3://$BUCKET/logs/transformation_logs/ --region $REGION | tail -5
else
	echo -e "${YELLOW}⚠ No transformation logs found (transformation job may not have run yet)${NC}"
fi

echo ""

# ============================================================================
# CHECK 11: CURATED DATA
# ============================================================================
echo -e "${YELLOW}[CHECK 11] Verifying curated data...${NC}"

CURATED_DATA=$(aws s3 ls s3://$BUCKET/curated/countries/ --region $REGION --recursive 2>/dev/null | wc -l)

if [ $CURATED_DATA -gt 0 ]; then
	echo -e "${GREEN}✓ Curated data found${NC}"
	echo "  Location: s3://$BUCKET/curated/countries/"
	echo "  Files:"
	aws s3 ls s3://$BUCKET/curated/countries/ --region $REGION --recursive | tail -5
else
	echo -e "${YELLOW}⚠ No curated data found (transformation job may not have run yet)${NC}"
fi

echo ""

# ============================================================================
# FINAL SUMMARY
# ============================================================================
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              VERIFICATION COMPLETE                    ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

echo "Deployment Status:"
echo "  ✅ Lambda Function: $([ -n "$LAMBDA_EXISTS" ] && echo 'DEPLOYED' || echo 'MISSING')"
echo "  ✅ Lambda Test: $([ "$STATUS" = "200" ] && echo 'PASSED' || echo 'FAILED')"
echo "  ✅ Ingestion Logs: $([ $INGESTION_LOGS -gt 0 ] && echo 'FOUND' || echo 'MISSING')"
echo "  ✅ Raw Data: $([ $RAW_DATA -gt 0 ] && echo 'FOUND' || echo 'MISSING')"
echo "  ✅ Validation Job: $([ -n "$VALIDATION_JOB" ] && echo 'DEPLOYED' || echo 'MISSING')"
echo "  ✅ Transformation Job: $([ -n "$TRANSFORM_JOB" ] && echo 'DEPLOYED' || echo 'MISSING')"
echo "  ✅ Glue Scripts: $([ -n "$VALIDATION_SCRIPT" ] && [ -n "$TRANSFORM_SCRIPT" ] && echo 'UPLOADED' || echo 'MISSING')"
echo "  ✅ Validation Logs: $([ $VALIDATION_LOGS -gt 0 ] && echo 'FOUND' || echo 'NOT YET')"
echo "  ✅ Transformation Logs: $([ $TRANSFORM_LOGS -gt 0 ] && echo 'FOUND' || echo 'NOT YET')"
echo ""

if [ -n "$LAMBDA_EXISTS" ] && [ "$STATUS" = "200" ] && [ $INGESTION_LOGS -gt 0 ] && [ $RAW_DATA -gt 0 ] && [ -n "$VALIDATION_JOB" ] && [ -n "$TRANSFORM_JOB" ]; then
	echo -e "${GREEN}✅ DEPLOYMENT SUCCESSFUL!${NC}"
	echo ""
	echo "Next steps:"
	echo "  1. Run validation job:"
	echo "     aws glue start-job-run --job-name country-population-validation --region $REGION"
	echo ""
	echo "  2. Run transformation job (after validation completes):"
	echo "     aws glue start-job-run --job-name country-population-transformation --region $REGION"
	echo ""
	echo "  3. Query results in Athena"
else
	echo -e "${RED}⚠ DEPLOYMENT INCOMPLETE${NC}"
	echo ""
	echo "Run ./deploy_final.sh to complete deployment"
fi
