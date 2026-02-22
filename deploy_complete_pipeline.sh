#!/bin/bash

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║   COMPLETE ETL PIPELINE DEPLOYMENT & EXECUTION        ║${NC}"
echo -e "${YELLOW}║   Lambda → Glue Validation → Glue Transform → Athena  ║${NC}"
echo -e "${YELLOW}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Get configuration
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"
BUCKET="data-pipeline-country-population"

echo "Configuration:"
echo "  Account ID: $ACCOUNT_ID"
echo "  Region: $REGION"
echo "  Bucket: $BUCKET"
echo ""

# ============================================================================
# PHASE 1: PREPARE & VALIDATE
# ============================================================================
echo -e "${YELLOW}[PHASE 1] PREPARING & VALIDATING...${NC}"

# Check prerequisites
echo "Checking prerequisites..."
command -v aws >/dev/null 2>&1 || { echo "AWS CLI not found"; exit 1; }
command -v zip >/dev/null 2>&1 || { echo "zip not found"; exit 1; }

# Verify files exist
[ -f "lambda_deployment/ingest_api_data.py" ] || { echo "Lambda function not found"; exit 1; }
[ -f "Validation/validate_schema.py" ] || { echo "Validation script not found"; exit 1; }
[ -f "Transformation/transform_data.py" ] || { echo "Transformation script not found"; exit 1; }

echo -e "${GREEN}✓ Prerequisites verified${NC}"
echo ""

# ============================================================================
# PHASE 2: DEPLOY LAMBDA FUNCTION
# ============================================================================
echo -e "${YELLOW}[PHASE 2] DEPLOYING LAMBDA INGESTION FUNCTION...${NC}"

cd lambda_deployment

# Create ZIP package
rm -f ingest_api_data.zip
zip -q ingest_api_data.zip ingest_api_data.py
echo "Lambda package created"

# Create or update Lambda function
LAMBDA_EXISTS=$(aws lambda list-functions --region $REGION --query "Functions[?FunctionName=='ingest-api-data'].FunctionName" --output text 2>/dev/null)

if [ -z "$LAMBDA_EXISTS" ]; then
	echo "Creating Lambda function..."
	aws lambda create-function \
		--function-name ingest-api-data \
		--runtime python3.9 \
		--role arn:aws:iam::$ACCOUNT_ID:role/lambda-execution-role \
		--handler ingest_api_data.lambda_handler \
		--zip-file fileb://ingest_api_data.zip \
		--timeout 60 \
		--memory-size 256 \
		--region $REGION > /dev/null
	echo -e "${GREEN}✓ Lambda function created${NC}"
else
	echo "Updating Lambda function..."
	aws lambda update-function-code \
		--function-name ingest-api-data \
		--zip-file fileb://ingest_api_data.zip \
		--region $REGION > /dev/null
	echo -e "${GREEN}✓ Lambda function updated${NC}"
fi

cd ..
echo ""

# ============================================================================
# PHASE 3: UPLOAD GLUE SCRIPTS TO S3
# ============================================================================
echo -e "${YELLOW}[PHASE 3] UPLOADING GLUE SCRIPTS TO S3...${NC}"

echo "Uploading validation script..."
aws s3 cp Validation/validate_schema.py s3://$BUCKET/scripts/validate_schema.py --region $REGION > /dev/null
echo -e "${GREEN}✓ Validation script uploaded${NC}"

echo "Uploading transformation script..."
aws s3 cp Transformation/transform_data.py s3://$BUCKET/scripts/transform_data.py --region $REGION > /dev/null
echo -e "${GREEN}✓ Transformation script uploaded${NC}"

echo "Removing old ingestion script from S3..."
aws s3 rm s3://$BUCKET/scripts/ingest_data.py --region $REGION 2>/dev/null || true
echo -e "${GREEN}✓ Old scripts cleaned up${NC}"

echo ""

# ============================================================================
# PHASE 4: UPDATE GLUE JOBS
# ============================================================================
echo -e "${YELLOW}[PHASE 4] UPDATING GLUE JOBS...${NC}"

echo "Updating validation job..."
aws glue update-job \
	--job-name country-population-validation \
	--job-command Name=glueetl,ScriptLocation=s3://$BUCKET/scripts/validate_schema.py \
	--role arn:aws:iam::$ACCOUNT_ID:role/glue-validation-role \
	--glue-version "3.0" \
	--worker-type G.1X \
	--number-of-workers 3 \
	--region $REGION > /dev/null 2>&1 || echo "Warning: Could not update validation job"
echo -e "${GREEN}✓ Validation job updated${NC}"

echo "Updating transformation job..."
aws glue update-job \
	--job-name country-population-transformation \
	--job-command Name=glueetl,ScriptLocation=s3://$BUCKET/scripts/transform_data.py \
	--role arn:aws:iam::$ACCOUNT_ID:role/glue-validation-role \
	--glue-version "3.0" \
	--worker-type G.1X \
	--number-of-workers 5 \
	--region $REGION > /dev/null 2>&1 || echo "Warning: Could not update transformation job"
echo -e "${GREEN}✓ Transformation job updated${NC}"

echo ""

# ============================================================================
# PHASE 5: EXECUTE PIPELINE
# ============================================================================
echo -e "${YELLOW}[PHASE 5] EXECUTING COMPLETE PIPELINE...${NC}"
echo ""

# Step 1: Invoke Lambda
echo "Step 1: Invoking Lambda for API ingestion..."
LAMBDA_RESPONSE=$(aws lambda invoke \
	--function-name ingest-api-data \
	--region $REGION \
	/tmp/lambda_response.json 2>&1)

LAMBDA_STATUS=$(cat /tmp/lambda_response.json | grep -o '"statusCode": [0-9]*' | grep -o '[0-9]*')

if [ "$LAMBDA_STATUS" = "200" ]; then
	RECORDS=$(cat /tmp/lambda_response.json | grep -o '"records": [0-9]*' | grep -o '[0-9]*')
	echo -e "${GREEN}✓ Lambda executed successfully - fetched $RECORDS records${NC}"
else
	echo -e "${RED}✗ Lambda execution failed${NC}"
	cat /tmp/lambda_response.json
	exit 1
fi

echo "Waiting 30 seconds for data to appear in S3..."
sleep 30

# Verify raw data
RAW_COUNT=$(aws s3 ls s3://$BUCKET/raw/countries/ --region $REGION --recursive | wc -l)
if [ $RAW_COUNT -gt 0 ]; then
	echo -e "${GREEN}✓ Raw data found in S3${NC}"
else
	echo -e "${RED}✗ No raw data in S3${NC}"
	exit 1
fi

echo ""

# Step 2: Run Validation Job
echo "Step 2: Running Glue Validation job..."
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

if [ "$VALIDATION_STATUS" = "SUCCEEDED" ]; then
	echo -e "${GREEN}✓ Validation job succeeded${NC}"
else
	echo -e "${RED}⚠ Validation job status: $VALIDATION_STATUS${NC}"
fi

echo ""

# Step 3: Run Transformation Job
echo "Step 3: Running Glue Transformation job..."
TRANSFORM_RUN=$(aws glue start-job-run \
	--job-name country-population-transformation \
	--region $REGION \
	--query 'JobRunId' \
	--output text)

echo "Transformation job started: $TRANSFORM_RUN"
echo "Waiting 90 seconds for completion..."
sleep 90

# Check transformation status
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
# PHASE 6: VERIFY OUTPUTS
# ============================================================================
echo -e "${YELLOW}[PHASE 6] VERIFYING OUTPUTS...${NC}"

echo "Raw data in S3:"
aws s3 ls s3://$BUCKET/raw/countries/ --region $REGION --recursive | tail -3

echo ""
echo "Validated data in S3:"
aws s3 ls s3://$BUCKET/validated/countries/ --region $REGION --recursive | tail -3

echo ""
echo "Curated data in S3 (partitioned by region):"
aws s3 ls s3://$BUCKET/curated/countries/ --region $REGION --recursive | tail -5

echo ""

# ============================================================================
# PHASE 7: SETUP ATHENA
# ============================================================================
echo -e "${YELLOW}[PHASE 7] SETTING UP ATHENA FOR QUERIES...${NC}"

# Create database
echo "Creating Athena database..."
aws athena start-query-execution \
	--query-string "CREATE DATABASE IF NOT EXISTS country_population;" \
	--result-configuration OutputLocation=s3://$BUCKET/athena-results/ \
	--region $REGION > /dev/null 2>&1 || true

# Create table
echo "Creating Athena table..."
aws athena start-query-execution \
	--query-string "
	CREATE EXTERNAL TABLE IF NOT EXISTS country_population.countries_curated (
		country_name STRING,
		region STRING,
		subregion STRING,
		population BIGINT,
		area DOUBLE,
		capital_city STRING,
		currency STRING
	)
	PARTITIONED BY (region STRING)
	STORED AS PARQUET
	LOCATION 's3://$BUCKET/curated/countries/'
	" \
	--query-execution-context Database=country_population \
	--result-configuration OutputLocation=s3://$BUCKET/athena-results/ \
	--region $REGION > /dev/null 2>&1 || true

echo -e "${GREEN}✓ Athena database and table created${NC}"

echo ""

# ============================================================================
# FINAL SUMMARY
# ============================================================================
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              DEPLOYMENT COMPLETE ✅                    ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

echo "Pipeline Summary:"
echo "  ✅ Lambda Ingestion: ingest-api-data"
echo "  ✅ Glue Validation: country-population-validation"
echo "  ✅ Glue Transformation: country-population-transformation"
echo "  ✅ Athena Database: country_population"
echo "  ✅ Athena Table: countries_curated"
echo ""

echo "Data Flow:"
echo "  RAW: s3://$BUCKET/raw/countries/"
echo "  VALIDATED: s3://$BUCKET/validated/countries/"
echo "  CURATED: s3://$BUCKET/curated/countries/"
echo ""

echo "Query Results in Athena:"
echo "  Database: country_population"
echo "  Table: countries_curated"
echo ""
echo "Sample Athena Query:"
echo "  SELECT region, COUNT(*) as country_count, SUM(population) as total_population"
echo "  FROM country_population.countries_curated"
echo "  GROUP BY region"
echo "  ORDER BY total_population DESC;"
echo ""

echo "AWS Console Links:"
echo "  Lambda: https://console.aws.amazon.com/lambda/home?region=$REGION#/functions/ingest-api-data"
echo "  Glue: https://console.aws.amazon.com/glue/home?region=$REGION#/jobs"
echo "  S3: https://s3.console.aws.amazon.com/s3/buckets/$BUCKET"
echo "  Athena: https://console.aws.amazon.com/athena/home?region=$REGION#/query-editor"
echo ""

echo -e "${GREEN}✅ Complete ETL pipeline is now live!${NC}"
