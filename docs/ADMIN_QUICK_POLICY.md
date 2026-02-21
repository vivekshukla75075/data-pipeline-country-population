# Quick Policy Creation for AWS Admin

## Fastest Way: Copy-Paste in AWS Console

### Step 1: Go to AWS Console

1. Open AWS Console: https://console.aws.amazon.com
2. Go to **IAM → Policies → Create policy**
3. Click **JSON** tab

### Step 2: Copy This Policy JSON

**Copy everything below (from `{` to `}`)**

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

### Step 3: Paste & Create

1. Right-click in the JSON editor → **Paste**
2. Click **Next: Tags**
3. Click **Next: Review**
4. Policy name: **`DataPipelineDeploymentPolicy`**
5. Click **Create policy**

---

## Verify Policy Was Created

Run this command:

```bash
aws iam get-policy --policy-name DataPipelineDeploymentPolicy
```

You should see output with the policy ARN.

---

## Attach to User

### In AWS Console:

1. Go to **IAM → Users → data-pipeline-country-population**
2. Click **Permissions** tab
3. Click **Add permissions → Attach policies directly**
4. Search: **`DataPipelineDeploymentPolicy`**
5. Select it
6. Click **Attach policy**

### Or via CLI:

```bash
# Get your AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Attach the policy
aws iam attach-user-policy \
  --user-name data-pipeline-country-population \
  --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/DataPipelineDeploymentPolicy
```

---

## Verify Attachment

```bash
aws iam list-attached-user-policies --user-name data-pipeline-country-population
```

Should show: `DataPipelineDeploymentPolicy`

---

## Now User Can Deploy

The user can now run:

```bash
./infrastructure/scripts/full_deployment.sh
```

All resources will be created automatically! ✅
