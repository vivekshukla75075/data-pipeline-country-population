#!/bin/bash

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║         ADD LAMBDA PERMISSIONS TO IAM USER             ║${NC}"
echo -e "${YELLOW}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
IAM_USER="data-pipeline-country-population"
LAMBDA_FUNCTION="ingest-api-data"
REGION="us-east-1"

echo "Account ID: $ACCOUNT_ID"
echo "IAM User: $IAM_USER"
echo "Lambda Function: $LAMBDA_FUNCTION"
echo ""

# ============================================================================
# STEP 1: CREATE LAMBDA POLICY
# ============================================================================
echo -e "${YELLOW}[STEP 1] Creating Lambda update policy...${NC}"

cat > /tmp/lambda_policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "UpdateLambdaFunction",
      "Effect": "Allow",
      "Action": [
        "lambda:UpdateFunctionCode",
        "lambda:GetFunction",
        "lambda:GetFunctionConfiguration",
        "lambda:InvokeFunction"
      ],
      "Resource": "arn:aws:lambda:*:ACCOUNT_ID:function:ingest-api-data"
    },
    {
      "Sid": "CloudWatchLogsForLambda",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams",
        "logs:GetLogEvents"
      ],
      "Resource": "arn:aws:logs:*:ACCOUNT_ID:log-group:/aws/lambda/*"
    }
  ]
}
EOF

# Replace ACCOUNT_ID in policy
sed -i "s/ACCOUNT_ID/$ACCOUNT_ID/g" /tmp/lambda_policy.json

echo -e "${GREEN}✓ Policy created${NC}"
echo ""

# ============================================================================
# STEP 2: ATTACH POLICY TO IAM USER
# ============================================================================
echo -e "${YELLOW}[STEP 2] Attaching policy to IAM user...${NC}"

aws iam put-user-policy \
  --user-name $IAM_USER \
  --policy-name LambdaUpdatePolicy \
  --policy-document file:///tmp/lambda_policy.json

echo -e "${GREEN}✓ Policy attached to user: $IAM_USER${NC}"
echo ""

# ============================================================================
# STEP 3: VERIFY POLICY
# ============================================================================
echo -e "${YELLOW}[STEP 3] Verifying policy...${NC}"

aws iam get-user-policy \
  --user-name $IAM_USER \
  --policy-name LambdaUpdatePolicy \
  --query 'UserPolicy.PolicyDocument' \
  --output json | jq '.'

echo -e "${GREEN}✓ Policy verified${NC}"
echo ""

# ============================================================================
# STEP 4: TEST LAMBDA PERMISSIONS
# ============================================================================
echo -e "${YELLOW}[STEP 4] Testing Lambda permissions...${NC}"

# Check if Lambda function exists
LAMBDA_ARN=$(aws lambda get-function \
  --function-name $LAMBDA_FUNCTION \
  --region $REGION \
  --query 'Configuration.FunctionArn' \
  --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$LAMBDA_ARN" != "NOT_FOUND" ]; then
  echo -e "${GREEN}✓ Lambda function found: $LAMBDA_ARN${NC}"
else
  echo -e "${RED}✗ Lambda function not found${NC}"
  echo "  You may need to create the Lambda function first"
fi

echo ""

# ============================================================================
# FINAL SUMMARY
# ============================================================================
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              PERMISSIONS UPDATED ✅                   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

echo "Summary:"
echo "  ✅ Policy created with Lambda permissions"
echo "  ✅ Policy attached to IAM user: $IAM_USER"
echo "  ✅ IAM user can now:"
echo "     - lambda:UpdateFunctionCode"
echo "     - lambda:GetFunction"
echo "     - lambda:GetFunctionConfiguration"
echo "     - lambda:InvokeFunction"
echo ""

echo "Next steps:"
echo "  1. Push changes to GitHub"
echo "  2. The GitHub Actions workflow will automatically:"
echo "     - Deploy Lambda function"
echo "     - Update Glue jobs"
echo "     - Test execution"
echo ""

echo -e "${GREEN}✅ IAM permissions updated successfully!${NC}"

# Cleanup
rm -f /tmp/lambda_policy.json
