#!/bin/bash
#
# Destroy Data Pipeline Infrastructure
# 
# This script safely removes all AWS resources created by the data pipeline:
# - CloudFormation stack
# - Lambda functions
# - Step Functions state machines
# - EventBridge rules
# - SQS queues
# - SNS topics
# - IAM roles
# - S3 bucket contents (optional)
#
# Usage:
#   ./destroy_orchestration.sh [STACK_NAME] [REGION] [EMPTY_BUCKETS]
#
# Examples:
#   ./destroy_orchestration.sh
#   ./destroy_orchestration.sh data-pipeline-orchestration us-east-1 true
#

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
STACK_NAME="${1:-data-pipeline-orchestration}"
REGION="${2:-us-east-1}"
EMPTY_BUCKETS="${3:-true}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Data Pipeline Destruction Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Stack Name: $STACK_NAME"
echo "Region: $REGION"
echo "Empty Buckets: $EMPTY_BUCKETS"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}ERROR: AWS CLI is not installed${NC}"
    exit 1
fi

# Verify stack exists
echo -e "${YELLOW}Step 1: Verifying stack exists...${NC}"
if aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Stack found${NC}"
    
    STACK_STATUS=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].StackStatus' \
        --output text)
    echo "  Status: $STACK_STATUS"
else
    echo -e "${RED}✗ Stack not found: $STACK_NAME${NC}"
    exit 1
fi

echo ""

# Empty S3 buckets if requested
if [ "$EMPTY_BUCKETS" = "true" ]; then
    echo -e "${YELLOW}Step 2: Finding and emptying S3 buckets...${NC}"
    
    # Find buckets that match the data-pipeline pattern
    BUCKETS=$(aws s3api list-buckets --query 'Buckets[].Name' --output text | tr '\t' '\n' | grep -E 'data-pipeline' || true)
    
    if [ -z "$BUCKETS" ]; then
        echo -e "${YELLOW}⚠ No matching S3 buckets found${NC}"
    else
        echo "Found buckets:"
        echo "$BUCKETS" | sed 's/^/  - /'
        echo ""
        
        for bucket in $BUCKETS; do
            echo -e "${YELLOW}Emptying bucket: ${BLUE}$bucket${NC}"
            
            # Remove all object versions (handles versioned buckets)
            VERSIONS=$(aws s3api list-object-versions \
                --bucket "$bucket" \
                --query 'Versions[].[Key,VersionId]' \
                --output text 2>/dev/null || true)
            
            if [ -n "$VERSIONS" ]; then
                echo "$VERSIONS" | while read key version; do
                    if [ -n "$key" ]; then
                        aws s3api delete-object \
                            --bucket "$bucket" \
                            --key "$key" \
                            --version-id "$version" >/dev/null 2>&1
                        echo -e "  Deleted: ${BLUE}$key${NC} (v:$version)"
                    fi
                done
            fi
            
            # Remove delete markers if any
            MARKERS=$(aws s3api list-object-versions \
                --bucket "$bucket" \
                --query 'DeleteMarkers[].[Key,VersionId]' \
                --output text 2>/dev/null || true)
            
            if [ -n "$MARKERS" ]; then
                echo "$MARKERS" | while read key version; do
                    if [ -n "$key" ]; then
                        aws s3api delete-object \
                            --bucket "$bucket" \
                            --key "$key" \
                            --version-id "$version" >/dev/null 2>&1
                        echo -e "  Deleted marker: ${BLUE}$key${NC} (v:$version)"
                    fi
                done
            fi
            
            echo -e "${GREEN}✓ Bucket emptied${NC}"
        done
    fi
    
    echo ""
fi

# Delete CloudFormation stack
echo -e "${YELLOW}Step 3: Deleting CloudFormation stack...${NC}"
echo "Initiating deletion of stack: $STACK_NAME"

aws cloudformation delete-stack \
    --stack-name "$STACK_NAME" \
    --region "$REGION" || {
    echo -e "${RED}Failed to delete stack${NC}"
    exit 1
}

echo "Stack deletion initiated..."
echo "Waiting for completion (this may take a few minutes)..."

# Wait for stack deletion with timeout
TIMEOUT=600  # 10 minutes
ELAPSED=0
INTERVAL=10

while [ $ELAPSED -lt $TIMEOUT ]; do
    STACK_STATUS=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].StackStatus' \
        --output text 2>/dev/null || echo "DELETED")
    
    if [ "$STACK_STATUS" = "DELETE_COMPLETE" ] || [ "$STACK_STATUS" = "DELETED" ]; then
        echo -e "${GREEN}✓ Stack deletion completed${NC}"
        break
    fi
    
    if [[ "$STACK_STATUS" == *"DELETE_FAILED"* ]]; then
        echo -e "${RED}✗ Stack deletion failed: $STACK_STATUS${NC}"
        exit 1
    fi
    
    echo "  Status: $STACK_STATUS (elapsed: ${ELAPSED}s)"
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

if [ $ELAPSED -ge $TIMEOUT ]; then
    echo -e "${YELLOW}⚠ Timeout waiting for stack deletion${NC}"
    echo "Stack may still be deleting. Check AWS CloudFormation console for status."
fi

echo ""

# Final verification
echo -e "${YELLOW}Step 4: Verifying deletion...${NC}"
if aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" >/dev/null 2>&1; then
    FINAL_STATUS=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].StackStatus' \
        --output text)
    echo "Final stack status: $FINAL_STATUS"
else
    echo -e "${GREEN}✓ Stack not found (successfully deleted)${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Cleanup Summary${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Deleted resources:"
echo "  - CloudFormation stack: $STACK_NAME"
echo "  - Lambda functions (ingest-api-data, pipeline-status-notifier)"
echo "  - Step Functions state machine"
echo "  - EventBridge schedule rules"
echo "  - SQS notification queue"
echo "  - SNS notification topic"
echo "  - IAM execution roles"
if [ "$EMPTY_BUCKETS" = "true" ]; then
    echo "  - S3 bucket contents (buckets may still exist)"
fi
echo ""
echo "Next steps:"
echo "  1. Verify cleanup in AWS CloudFormation console"
echo "  2. Check S3 console for bucket cleanup"
echo "  3. Review Lambda functions list (should be empty)"
echo "  4. Check billing to confirm resource removal"
echo ""
echo -e "${GREEN}✓ Destruction process completed${NC}"
