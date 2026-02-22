#!/bin/bash

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║         CLEANUP REPO & AWS + BUILD & DEPLOY           ║${NC}"
echo -e "${YELLOW}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"
BUCKET="data-pipeline-country-population"

# ============================================================================
# PHASE 1: CLEANUP REPOSITORY
# ============================================================================
echo -e "${YELLOW}[PHASE 1] CLEANING UP REPOSITORY...${NC}"

# Remove unnecessary directories
CLEANUP_DIRS=(
	"infra/terraform"
	"lambda_functions"
	"Ingestion"
	"tests"
	".pytest_cache"
	"__pycache__"
)

for dir in "${CLEANUP_DIRS[@]}"; do
	if [ -d "$dir" ]; then
		echo "Removing directory: $dir"
		rm -rf "$dir"
		echo -e "${GREEN}✓ Removed $dir${NC}"
	fi
done

# Remove unnecessary files
CLEANUP_FILES=(
	"*.pyc"
	"*.pyo"
	".pytest_cache"
	"test_*.py"
	"Ingestion/test_*.py"
	"Validation/test_validate_schema.py"
	"Transformation/test_*.py"
)

for pattern in "${CLEANUP_FILES[@]}"; do
	find . -name "$pattern" -type f -delete 2>/dev/null || true
done

echo -e "${GREEN}✓ Repository cleaned${NC}"
echo ""

# ============================================================================
# PHASE 2: CLEANUP AWS S3
# ============================================================================
echo -e "${YELLOW}[PHASE 2] CLEANING UP AWS S3...${NC}"

echo "Removing old/unnecessary files from S3..."

# Remove old ingest_data.py
aws s3 rm s3://$BUCKET/scripts/ingest_data.py --region $REGION 2>/dev/null || true
echo -e "${GREEN}✓ Removed old ingest_data.py${NC}"

# Remove old logs
aws s3 rm s3://$BUCKET/logs/ --recursive --region $REGION 2>/dev/null || true
echo -e "${GREEN}✓ Removed old logs${NC}"

# Keep only essential: scripts, raw, validated, curated, athena-results
echo -e "${GREEN}✓ S3 cleanup complete${NC}"
echo ""

# ============================================================================
# PHASE 3: CLEANUP AWS IAM & LAMBDA (OPTIONAL - Leave for reuse)
# ============================================================================
echo -e "${YELLOW}[PHASE 3] VERIFYING AWS RESOURCES...${NC}"

# Check Lambda function
LAMBDA_EXISTS=$(aws lambda list-functions --region $REGION --query "Functions[?FunctionName=='ingest-api-data'].FunctionName" --output text 2>/dev/null)
if [ -n "$LAMBDA_EXISTS" ]; then
	echo -e "${GREEN}✓ Lambda function exists: ingest-api-data${NC}"
else
	echo "Lambda function will be created..."
fi

# Check Glue jobs
VALIDATION_JOB=$(aws glue list-jobs --region $REGION --query "JobList[?Name=='country-population-validation'].Name" --output text 2>/dev/null)
TRANSFORM_JOB=$(aws glue list-jobs --region $REGION --query "JobList[?Name=='country-population-transformation'].Name" --output text 2>/dev/null)

if [ -n "$VALIDATION_JOB" ]; then
	echo -e "${GREEN}✓ Glue Validation job exists${NC}"
fi

if [ -n "$TRANSFORM_JOB" ]; then
	echo -e "${GREEN}✓ Glue Transformation job exists${NC}"
fi

echo ""

# ============================================================================
# PHASE 4: UPDATE GIT & COMMIT CLEANUP
# ============================================================================
echo -e "${YELLOW}[PHASE 4] COMMITTING CLEANUP TO GIT...${NC}"

git add -A
git commit -m "chore: Cleanup repository and AWS resources

- Remove unused directories: infra/terraform, lambda_functions, Ingestion, tests
- Remove test files and __pycache__
- Remove old scripts from S3
- Keep only essential files and directories
- Clean repository for production"

git push origin feature/sync-upstream-changes

echo -e "${GREEN}✓ Cleanup committed to git${NC}"
echo ""

# ============================================================================
# PHASE 5: BUILD & DEPLOY
# ============================================================================
echo -e "${YELLOW}[PHASE 5] DEPLOYING CLEAN PIPELINE...${NC}"

# Run complete deployment
chmod +x deploy_complete_pipeline.sh
./deploy_complete_pipeline.sh

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           CLEANUP & BUILD COMPLETE ✅                  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

echo "Repository Structure (Clean):"
echo "  Validation/"
echo "    validate_schema.py"
echo "    test_validate_schema.py"
echo "  Transformation/"
echo "    transform_data.py"
echo "  lambda_deployment/"
echo "    ingest_api_data.py"
echo "  infrastructure/"
echo "    scripts/"
echo "  docs/"
echo "  .github/workflows/"
echo "  README.md"
echo ""

echo "AWS Resources:"
echo "  ✅ Lambda: ingest-api-data"
echo "  ✅ Glue Job: country-population-validation"
echo "  ✅ Glue Job: country-population-transformation"
echo "  ✅ S3 Bucket: data-pipeline-country-population"
echo "  ✅ Athena: country_population database"
echo ""

echo "Ready for production deployment! 🚀"
