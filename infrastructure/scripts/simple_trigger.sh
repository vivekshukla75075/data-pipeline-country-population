#!/bin/bash

# Simple script to trigger Glue jobs manually

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}========== Manual ETL Pipeline Trigger ==========${NC}"

AWS_REGION="us-east-1"

# Step 1: Trigger Ingestion
echo -e "${YELLOW}[1/3] Triggering Ingestion Job...${NC}"
INGESTION_RUN=$(aws glue start-job-run \
  --job-name country-population-ingestion \
  --region $AWS_REGION \
  --query 'JobRunId' \
  --output text 2>/dev/null || echo "FAILED")

if [ "$INGESTION_RUN" != "FAILED" ]; then
  echo -e "${GREEN}✓ Ingestion job started: $INGESTION_RUN${NC}"
  echo "Waiting for ingestion to complete..."
  sleep 60
else
  echo -e "${YELLOW}⚠️ Could not start ingestion job${NC}"
fi

# Step 2: Trigger Validation
echo -e "${YELLOW}[2/3] Triggering Validation Job...${NC}"
VALIDATION_RUN=$(aws glue start-job-run \
  --job-name country-population-validation \
  --region $AWS_REGION \
  --query 'JobRunId' \
  --output text 2>/dev/null || echo "FAILED")

if [ "$VALIDATION_RUN" != "FAILED" ]; then
  echo -e "${GREEN}✓ Validation job started: $VALIDATION_RUN${NC}"
  echo "Waiting for validation to complete..."
  sleep 60
else
  echo -e "${YELLOW}⚠️ Could not start validation job${NC}"
fi

# Step 3: Trigger Transformation
echo -e "${YELLOW}[3/3] Triggering Transformation Job...${NC}"
TRANSFORMATION_RUN=$(aws glue start-job-run \
  --job-name country-population-transformation \
  --region $AWS_REGION \
  --query 'JobRunId' \
  --output text 2>/dev/null || echo "FAILED")

if [ "$TRANSFORMATION_RUN" != "FAILED" ]; then
  echo -e "${GREEN}✓ Transformation job started: $TRANSFORMATION_RUN${NC}"
else
  echo -e "${YELLOW}⚠️ Could not start transformation job${NC}"
fi

# Summary
echo -e "${GREEN}"
echo "========== Pipeline Triggered =========="
echo "Monitor jobs at:"
echo "https://console.aws.amazon.com/glue/home?region=$AWS_REGION#/jobs"
echo ""
echo "Job Run IDs:"
echo "- Ingestion: $INGESTION_RUN"
echo "- Validation: $VALIDATION_RUN"
echo "- Transformation: $TRANSFORMATION_RUN"
echo "========================================="
echo -e "${NC}"
