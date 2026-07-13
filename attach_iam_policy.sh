#!/bin/bash

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}IAM Policy Attachment Script${NC}"
echo -e "${BLUE}================================================${NC}"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}✗ AWS CLI not found. Please install it first.${NC}"
    exit 1
fi

# Get current user
CURRENT_USER=$(aws sts get-caller-identity --query User --output text 2>/dev/null || echo "unknown")
echo -e "${BLUE}Current AWS User: $CURRENT_USER${NC}"
echo ""

# Define variables
IAM_USER="data-pipeline-country-population"
POLICY_NAME="CloudFormationDeploymentPolicy"
POLICY_FILE="infra/iam/cloudformation_deployment_policy.json"

# Check if policy file exists
if [ ! -f "$POLICY_FILE" ]; then
    echo -e "${RED}✗ Policy file not found: $POLICY_FILE${NC}"
    exit 1
fi

echo -e "${YELLOW}Attaching policy to IAM user: $IAM_USER${NC}"
echo "Policy name: $POLICY_NAME"
echo ""

# Attach the policy
if aws iam put-user-policy \
    --user-name "$IAM_USER" \
    --policy-name "$POLICY_NAME" \
    --policy-document "file://$POLICY_FILE"; then
    echo -e "${GREEN}✓ Policy attached successfully${NC}"
else
    echo -e "${RED}✗ Failed to attach policy${NC}"
    exit 1
fi

echo ""

# Verify the policy was attached
echo -e "${BLUE}Verifying policy attachment...${NC}"
if aws iam get-user-policy \
    --user-name "$IAM_USER" \
    --policy-name "$POLICY_NAME" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Policy verified successfully${NC}"
    echo ""
    
    # Show policy summary
    echo -e "${BLUE}Policy includes permissions for:${NC}"
    echo "  ✓ CloudFormation (create, update, validate, delete stacks)"
    echo "  ✓ Lambda (create, update, delete functions)"
    echo "  ✓ IAM (pass role, create roles, attach policies)"
    echo "  ✓ Step Functions (create, manage state machines)"
    echo "  ✓ EventBridge (create and manage rules)"
    echo "  ✓ SNS/SQS (create topics, send messages)"
    echo "  ✓ Glue (create and run jobs)"
    echo "  ✓ S3 (bucket operations)"
    echo "  ✓ CloudWatch Logs (create log groups, write logs)"
else
    echo -e "${RED}✗ Policy verification failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}✓ IAM policy attachment complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. If using GitHub Actions, re-run the deploy workflow"
echo "2. If deploying locally, you can now run: ./deploy_all.sh"
echo ""
