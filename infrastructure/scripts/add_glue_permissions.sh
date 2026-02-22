#!/bin/bash

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Adding Glue update permissions to IAM user...${NC}"

ACCOUNT_ID="778277577996"
IAM_USER="data-pipeline-country-population"
REGION="us-east-1"

# Create Glue policy
cat > /tmp/glue_policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "GlueUpdateJob",
      "Effect": "Allow",
      "Action": [
        "glue:UpdateJob",
        "glue:GetJob",
        "glue:StartJobRun",
        "glue:GetJobRun"
      ],
      "Resource": "arn:aws:glue:${REGION}:${ACCOUNT_ID}:job/*"
    }
  ]
}
EOF

# Attach policy to IAM user
aws iam put-user-policy \
  --user-name "$IAM_USER" \
  --policy-name GlueUpdatePolicy \
  --policy-document file:///tmp/glue_policy.json

echo -e "${GREEN}✓ Glue update permissions added to IAM user${NC}"

# Verify
aws iam get-user-policy \
  --user-name "$IAM_USER" \
  --policy-name GlueUpdatePolicy

echo -e "${GREEN}✅ Glue permissions verified!${NC}"

rm -f /tmp/glue_policy.json
