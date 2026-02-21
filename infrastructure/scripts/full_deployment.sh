#!/bin/bash

set -e

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}========== Complete ETL Pipeline Deployment ==========${NC}"

# Step 1: Create S3 Bucket
echo -e "${YELLOW}[Step 1] Creating S3 Bucket...${NC}"
BUCKET_NAME="data-pipeline-country-population"
AWS_REGION="us-east-1"

if aws s3api head-bucket --bucket $BUCKET_NAME 2>/dev/null; then
  echo -e "${GREEN}✓ S3 bucket already exists${NC}"
else
  echo "Creating S3 bucket..."
  aws s3api create-bucket \
    --bucket $BUCKET_NAME \
    --region $AWS_REGION
  echo -e "${GREEN}✓ S3 bucket created${NC}"
fi

# Step 2: Upload scripts
echo -e "${YELLOW}[Step 2] Uploading scripts to S3...${NC}"
aws s3 cp Ingestion/ingest_data.py s3://$BUCKET_NAME/scripts/ 2>/dev/null || true
aws s3 cp Validation/validate_schema.py s3://$BUCKET_NAME/scripts/ 2>/dev/null || true
aws s3 cp Transformation/transform_data.py s3://$BUCKET_NAME/scripts/ 2>/dev/null || true
echo -e "${GREEN}✓ Scripts uploaded${NC}"

# Step 3: Run deployment pipeline
echo -e "${YELLOW}[Step 3] Running infrastructure deployment...${NC}"
if [ -f "infrastructure/scripts/deploy_pipeline.sh" ]; then
  chmod +x infrastructure/scripts/deploy_pipeline.sh
  ./infrastructure/scripts/deploy_pipeline.sh
else
  echo -e "${RED}❌ Deployment script not found${NC}"
  exit 1
fi

# Step 4: Upload sample data (optional)
echo -e "${YELLOW}[Step 4] Creating sample data...${NC}"
mkdir -p raw_data
cat > raw_data/sample_countries.json <<'EOF'
[
  {
    "name": {"common": "United States"},
    "region": "Americas",
    "population": 331900000,
    "area": 9833517,
    "capital": {"name": "Washington, D.C."}
  },
  {
    "name": {"common": "India"},
    "region": "Asia",
    "population": 1380004385,
    "area": 3287263,
    "capital": {"name": "New Delhi"}
  }
]
EOF

aws s3 cp raw_data/sample_countries.json s3://$BUCKET_NAME/raw/countries/countries_raw.json
echo -e "${GREEN}✓ Sample data uploaded${NC}"

# Step 5: Summary
echo -e "${GREEN}"
echo "========== Deployment Complete =========="
echo ""
echo "Next Steps:"
echo "1. Verify resources in AWS Console"
echo "2. Trigger the pipeline:"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "   aws stepfunctions start-execution \\"
echo "   --state-machine-arn arn:aws:states:$AWS_REGION:$ACCOUNT_ID:stateMachine:country-population-etl-pipeline \\"
echo "   --input '{}'"
echo ""
echo "Monitor execution:"
echo "   https://console.aws.amazon.com/states/home?region=$AWS_REGION"
echo "========================================="
echo -e "${NC}"
