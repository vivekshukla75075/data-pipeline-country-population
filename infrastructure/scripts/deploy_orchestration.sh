#!/bin/bash
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
STACK_NAME="${STACK_NAME:-data-pipeline-orchestration}"
TEMPLATE_FILE="infra/cloudformation/orchestration.yaml"
NOTIFICATION_LAMBDA_NAME="${NOTIFICATION_LAMBDA_NAME:-pipeline-status-notifier}"

if [[ ! -f "$TEMPLATE_FILE" ]]; then
  echo "Template not found: $TEMPLATE_FILE" >&2
  exit 1
fi

if ! command -v aws >/dev/null 2>&1; then
  echo "AWS CLI is required" >&2
  exit 1
fi

echo "Deploying orchestration stack $STACK_NAME in $REGION"
aws cloudformation deploy \
  --template-file "$TEMPLATE_FILE" \
  --stack-name "$STACK_NAME" \
  --parameter-overrides Environment=$ENVIRONMENT NotificationEmail=ntvs02011999@gmail.com \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "$REGION"

echo "Packaging notifier Lambda"
cd lambda_deployment
rm -f notify_pipeline_status.zip
zip -q notify_pipeline_status.zip notify_pipeline_status.py

echo "Creating or updating notifier Lambda"
aws lambda get-function --function-name "$NOTIFICATION_LAMBDA_NAME" --region "$REGION" >/dev/null 2>&1 || \
  aws lambda create-function \
    --function-name "$NOTIFICATION_LAMBDA_NAME" \
    --runtime python3.11 \
    --role "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/data-pipeline-notifier-role-$ENVIRONMENT" \
    --handler notify_pipeline_status.lambda_handler \
    --zip-file fileb://notify_pipeline_status.zip \
    --region "$REGION" >/dev/null

aws lambda update-function-code \
  --function-name "$NOTIFICATION_LAMBDA_NAME" \
  --zip-file fileb://notify_pipeline_status.zip \
  --region "$REGION" >/dev/null

echo "Deployment complete"
