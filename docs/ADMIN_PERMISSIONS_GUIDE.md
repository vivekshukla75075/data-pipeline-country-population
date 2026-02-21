# AWS Administrator Permissions Guide

## Overview

This guide helps AWS administrators grant the necessary permissions to enable automated ETL pipeline deployment.

## Permissions Required

Your IAM user needs permissions to:
1. Create and manage S3 buckets and objects
2. Create and manage Glue jobs
3. Create and manage Lambda functions
4. Create and manage IAM roles
5. Create and manage Step Functions
6. Create and manage Athena resources

---

## Step 1: Create Custom IAM Policy

### Option A: Via AWS Console

1. Go to **IAM → Policies → Create Policy**
2. Choose **JSON** tab
3. Paste the policy below
4. Click **Review Policy**
5. Name: `DataPipelineDeploymentPolicy`
6. Click **Create Policy**

### Option B: Via AWS CLI

```bash
cat > /tmp/data-pipeline-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3BucketManagement",
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:DeleteBucket",
        "s3:ListBucket",
        "s3:GetBucketLocation",
        "s3:GetBucketVersioning",
        "s3:PutBucketVersioning",
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucketVersions"
      ],
      "Resource": [
        "arn:aws:s3:::data-pipeline-country-population",
        "arn:aws:s3:::data-pipeline-country-population/*"
      ]
    },
    {
      "Sid": "GlueJobManagement",
      "Effect": "Allow",
      "Action": [
        "glue:CreateJob",
        "glue:UpdateJob",
        "glue:GetJob",
        "glue:GetJobs",
        "glue:DeleteJob",
        "glue:StartJobRun",
        "glue:GetJobRun",
        "glue:GetJobRuns",
        "glue:CreateDatabase",
        "glue:GetDatabase",
        "glue:CreateTable",
        "glue:UpdateTable",
        "glue:GetTable",
        "glue:DeleteTable",
        "glue:CreateCrawler",
        "glue:GetCrawler",
        "glue:StartCrawler"
      ],
      "Resource": "*"
    },
    {
      "Sid": "LambdaFunctionManagement",
      "Effect": "Allow",
      "Action": [
        "lambda:CreateFunction",
        "lambda:UpdateFunction",
        "lambda:UpdateFunctionCode",
        "lambda:GetFunction",
        "lambda:ListFunctions",
        "lambda:DeleteFunction",
        "lambda:AddPermission",
        "lambda:RemovePermission",
        "lambda:InvokeFunction"
      ],
      "Resource": "arn:aws:lambda:us-east-1:*:function:*"
    },
    {
      "Sid": "IAMRoleManagement",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:UpdateRole",
        "iam:GetRole",
        "iam:ListRoles",
        "iam:DeleteRole",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:PutRolePolicy",
        "iam:GetRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:ListAttachedRolePolicies",
        "iam:ListRolePolicies",
        "iam:PassRole"
      ],
      "Resource": [
        "arn:aws:iam::*:role/glue-validation-role",
        "arn:aws:iam::*:role/lambda-execution-role",
        "arn:aws:iam::*:role/step-functions-role",
        "arn:aws:iam::*:role/glue-crawler-role"
      ]
    },
    {
      "Sid": "StepFunctionsManagement",
      "Effect": "Allow",
      "Action": [
        "states:CreateStateMachine",
        "states:UpdateStateMachine",
        "states:DescribeStateMachine",
        "states:ListStateMachines",
        "states:StartExecution",
        "states:DescribeExecution",
        "states:StopExecution",
        "states:GetExecutionHistory"
      ],
      "Resource": "arn:aws:states:us-east-1:*:*"
    },
    {
      "Sid": "AthenaManagement",
      "Effect": "Allow",
      "Action": [
        "athena:CreateWorkGroup",
        "athena:GetWorkGroup",
        "athena:UpdateWorkGroup",
        "athena:DeleteWorkGroup",
        "athena:StartQueryExecution",
        "athena:GetQueryExecution",
        "athena:GetQueryResults",
        "athena:StopQueryExecution"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:GetLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams"
      ],
      "Resource": "arn:aws:logs:us-east-1:*:*"
    },
    {
      "Sid": "STSGetCallerIdentity",
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name DataPipelineDeploymentPolicy \
  --policy-document file:///tmp/data-pipeline-policy.json
```

---

## Step 2: Attach Policy to User

### Option A: Via AWS Console

1. Go to **IAM → Users → [User Name]**
2. Click **Add permissions → Attach policies directly**
3. Search for `DataPipelineDeploymentPolicy`
4. Select it
5. Click **Attach policy**

### Option B: Via AWS CLI

```bash
aws iam attach-user-policy \
  --user-name data-pipeline-country-population \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/DataPipelineDeploymentPolicy
```

Replace `ACCOUNT_ID` with your AWS account ID.

---

## Step 3: Verify Permissions

Run this command to verify the user has permissions:

```bash
# List attached policies
aws iam list-attached-user-policies --user-name data-pipeline-country-population

# Get inline policies
aws iam list-user-policies --user-name data-pipeline-country-population
```

---

## Step 4: Optional - Restrict to Specific Region (Enhanced Security)

For added security, create a role with specific region restrictions:

```bash
cat > /tmp/restricted-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RestrictedToUSEast1",
      "Effect": "Allow",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "us-east-1"
        }
      }
    }
  ]
}
EOF

aws iam put-user-policy \
  --user-name data-pipeline-country-population \
  --policy-name RegionRestriction \
  --policy-document file:///tmp/restricted-policy.json
```

---

## Step 5: Create Managed Policies for Easier Reuse

For easier management of multiple users, attach managed policies:

```bash
# Attach AWS managed Glue policy
aws iam attach-user-policy \
  --user-name data-pipeline-country-population \
  --policy-arn arn:aws:iam::aws:policy/AWSGlueServiceRole

# Attach AWS managed Lambda policy
aws iam attach-user-policy \
  --user-name data-pipeline-country-population \
  --policy-arn arn:aws:iam::aws:policy/AWSLambdaFullAccess

# Attach AWS managed S3 policy
aws iam attach-user-policy \
  --user-name data-pipeline-country-population \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# Attach AWS managed Step Functions policy
aws iam attach-user-policy \
  --user-name data-pipeline-country-population \
  --policy-arn arn:aws:iam::aws:policy/AWSStepFunctionsFullAccess
```

---

## Minimal Permissions (Least Privilege)

If you want to grant only minimum required permissions:

```bash
cat > /tmp/minimal-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:ListBucket",
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": [
        "arn:aws:s3:::data-pipeline-country-population",
        "arn:aws:s3:::data-pipeline-country-population/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "glue:CreateJob",
        "glue:GetJob",
        "glue:StartJobRun",
        "glue:CreateDatabase",
        "glue:GetDatabase"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:CreateFunction",
        "lambda:GetFunction",
        "lambda:UpdateFunctionCode"
      ],
      "Resource": "arn:aws:lambda:us-east-1:*:function:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:GetRole",
        "iam:PassRole"
      ],
      "Resource": "arn:aws:iam::*:role/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "states:CreateStateMachine",
        "states:StartExecution"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["sts:GetCallerIdentity"],
      "Resource": "*"
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name DataPipelineMinimalPolicy \
  --policy-document file:///tmp/minimal-policy.json
```

---

## Troubleshooting

### Permission Denied Errors

If user gets `AccessDenied` error:

1. Verify policy is attached:
   ```bash
   aws iam list-attached-user-policies --user-name USERNAME
   ```

2. Check policy content:
   ```bash
   aws iam get-policy --policy-arn arn:aws:iam::ACCOUNT_ID:policy/PolicyName
   ```

3. Test specific permission:
   ```bash
   aws s3 ls --debug 2>&1 | grep "Authorization"
   ```

### Policy Not Taking Effect

- Wait 1-2 minutes for policy to propagate
- Logout and login again
- Generate new access keys if needed

---

## Summary for Admin

**To enable automated deployment, grant:**

1. ✅ S3 bucket creation and management
2. ✅ Glue job creation and execution
3. ✅ Lambda function creation and updates
4. ✅ IAM role creation and policy attachment
5. ✅ Step Functions creation and execution
6. ✅ Athena query execution

**Use the policy JSON above and attach to the user.**

Once permissions are granted, the user can run:

```bash
chmod +x infrastructure/scripts/full_deployment.sh
./infrastructure/scripts/full_deployment.sh
```

Everything will deploy automatically! 🚀
