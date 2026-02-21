# AWS Administrator Setup Guide

Complete guide for AWS administrators to set up permissions and infrastructure for the ETL pipeline.

---

## Overview

This guide covers all admin tasks needed to enable automated ETL pipeline deployment:
1. Create IAM Policy
2. Attach Policy to User
3. Create Lambda Functions and Step Functions
4. Verify Setup

---

## Task 1: Create IAM Policy

### Option A: AWS Console (Recommended)

1. Go to: https://console.aws.amazon.com/iam/
2. Click: **Policies → Create Policy**
3. Click: **JSON** tab
4. Copy and paste this policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3Access",
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:ListBucket",
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:GetBucketVersioning",
        "s3:PutBucketVersioning"
      ],
      "Resource": [
        "arn:aws:s3:::data-pipeline-country-population",
        "arn:aws:s3:::data-pipeline-country-population/*"
      ]
    },
    {
      "Sid": "GlueAccess",
      "Effect": "Allow",
      "Action": [
        "glue:CreateJob",
        "glue:GetJob",
        "glue:GetJobs",
        "glue:StartJobRun",
        "glue:GetJobRun",
        "glue:CreateDatabase",
        "glue:GetDatabase",
        "glue:CreateTable",
        "glue:GetTable"
      ],
      "Resource": "*"
    },
    {
      "Sid": "LambdaAccess",
      "Effect": "Allow",
      "Action": [
        "lambda:CreateFunction",
        "lambda:GetFunction",
        "lambda:ListFunctions",
        "lambda:DeleteFunction",
        "lambda:InvokeFunction"
      ],
      "Resource": "arn:aws:lambda:us-east-1:*:function:*"
    },
    {
      "Sid": "IAMAccess",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:GetRole",
        "iam:AttachRolePolicy",
        "iam:PutRolePolicy",
        "iam:PassRole"
      ],
      "Resource": [
        "arn:aws:iam::*:role/glue-validation-role",
        "arn:aws:iam::*:role/lambda-execution-role",
        "arn:aws:iam::*:role/step-functions-role"
      ]
    },
    {
      "Sid": "StepFunctionsAccess",
      "Effect": "Allow",
      "Action": [
        "states:CreateStateMachine",
        "states:DescribeStateMachine",
        "states:StartExecution"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AthenaAccess",
      "Effect": "Allow",
      "Action": [
        "athena:CreateWorkGroup",
        "athena:StartQueryExecution",
        "athena:GetQueryExecution",
        "athena:GetQueryResults"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:*:*"
    },
    {
      "Sid": "GetCallerIdentity",
      "Effect": "Allow",
      "Action": "sts:GetCallerIdentity",
      "Resource": "*"
    }
  ]
}
```

5. Click: **Next: Tags → Next: Review**
6. Policy name: **`DataPipelineDeploymentPolicyupd`**
7. Click: **Create Policy**

---

## Task 2: Attach Policy to User

### Step 1: Get AWS Account ID

```bash
aws sts get-caller-identity --query Account --output text
```

Copy the 12-digit number (e.g., `123456789012`)

### Step 2: Attach Policy

Replace `YOUR_ACCOUNT_ID` with the actual ID from Step 1:

```bash
aws iam attach-user-policy \
  --user-name data-pipeline-country-population \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/DataPipelineDeploymentPolicyupd
```

### Step 3: Verify

```bash
aws iam list-attached-user-policies --user-name data-pipeline-country-population
```

Should show: `DataPipelineDeploymentPolicyupd` ✅

---

## Task 3: Create Lambda Functions and Step Functions

Once the policy is attached, the user can run:

```bash
chmod +x infrastructure/scripts/create_lambda_and_stepfunctions.sh
./infrastructure/scripts/create_lambda_and_stepfunctions.sh
```

This script will:
- ✅ Create 5 Lambda functions
- ✅ Create Step Functions state machine
- ✅ Set up required IAM roles

---

## Task 4: Verify Setup

### Check Lambda Functions

```bash
aws lambda list-functions --region us-east-1 --query 'Functions[?contains(FunctionName, `trigger`)].FunctionName' --output text
```

Should show: `trigger-ingestion trigger-validation trigger-transformation create-glue-catalog query-athena`

### Check Step Functions

```bash
aws stepfunctions list-state-machines --region us-east-1 --query 'stateMachines[].name' --output text
```

Should show: `country-population-etl-pipeline`

---

## Troubleshooting

### Policy Not Showing in Console

**Solution:** Use CLI method (Task 2 above) instead of console search.

### Lambda Functions Not Created

**Solution:** Run the Lambda/Step Functions creation script:

```bash
./infrastructure/scripts/create_lambda_and_stepfunctions.sh
```

### Permission Denied Errors

Check if policy is attached:

```bash
aws iam list-attached-user-policies --user-name data-pipeline-country-population
```

If policy is missing, re-run Task 2.

---

## Summary

**Admin Tasks:**
1. ✅ Create policy `DataPipelineDeploymentPolicyupd`
2. ✅ Attach to user `data-pipeline-country-population`
3. ✅ Have user run Lambda/Step Functions creation script
4. ✅ Verify resources in AWS Console

**User Can Then:**
- Run `./infrastructure/scripts/full_deployment.sh`
- Create Glue jobs automatically
- Deploy entire ETL pipeline

---

## Contact

For questions, refer to this guide or contact your AWS administrator.
