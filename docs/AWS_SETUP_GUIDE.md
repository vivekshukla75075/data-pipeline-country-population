# AWS Setup Guide for Data Pipeline Automation

This guide walks you through all the AWS configuration needed to run the automated data pipeline with EventBridge, Step Functions, Glue, Lambda, SQS, and SNS.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Step 1: Attach IAM Policy to Your User](#step-1-attach-iam-policy-to-your-user)
3. [Step 2: Create AWS Access Keys](#step-2-create-aws-access-keys)
4. [Step 3: Add GitHub Secrets](#step-3-add-github-secrets)
5. [Step 4: Deploy Infrastructure via GitHub Actions](#step-4-deploy-infrastructure-via-github-actions)
6. [Step 5: Verify Deployment](#step-5-verify-deployment)
7. [Step 6: Manual Trigger (Optional)](#step-6-manual-trigger-optional)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you start:
- AWS Account ID: `778277577996`
- IAM User: `data-pipeline-country-population`
- GitHub Repository: Set up and ready to receive pushes
- Your Email: `ntvs02011999@gmail.com` (for pipeline notifications)

---

## Step 1: Attach IAM Policy to Your User

### What This Does
Grants your IAM user permissions to create and manage the pipeline resources (Lambda, Glue, Step Functions, etc.).

### Instructions

1. **Go to AWS Console**
   - Navigate to: https://console.aws.amazon.com/iam/home
   - Login with your account

2. **Open IAM Users**
   - Left sidebar → "Users"
   - Click on `data-pipeline-country-population`

3. **Add the Policy**
   - Click the "Permissions" tab
   - Click "Add permissions" button
   - Select "Create inline policy"

4. **Paste the Policy**
   - Click "JSON" tab
   - Delete the default content
   - Copy and paste the entire policy from: `infra/iam/github_actions_policy.json`
   - Or use the full policy below:

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
        "lambda:InvokeFunction",
        "lambda:UpdateFunctionCode"
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
        "arn:aws:iam::*:role/step-functions-role",
        "arn:aws:iam::*:role/data-pipeline*"
      ]
    },
    {
      "Sid": "StepFunctionsAccess",
      "Effect": "Allow",
      "Action": [
        "states:CreateStateMachine",
        "states:UpdateStateMachine",
        "states:DescribeStateMachine",
        "states:StartExecution"
      ],
      "Resource": "*"
    },
    {
      "Sid": "EventBridgeAccess",
      "Effect": "Allow",
      "Action": [
        "events:CreateRule",
        "events:UpdateRule",
        "events:PutTargets",
        "events:RemoveTargets"
      ],
      "Resource": "*"
    },
    {
      "Sid": "SQSAccess",
      "Effect": "Allow",
      "Action": [
        "sqs:CreateQueue",
        "sqs:GetQueueUrl",
        "sqs:SetQueueAttributes"
      ],
      "Resource": "*"
    },
    {
      "Sid": "SNSAccess",
      "Effect": "Allow",
      "Action": [
        "sns:CreateTopic",
        "sns:GetTopicAttributes",
        "sns:Subscribe"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudFormationAccess",
      "Effect": "Allow",
      "Action": [
        "cloudformation:CreateStack",
        "cloudformation:UpdateStack",
        "cloudformation:DescribeStacks",
        "cloudformation:DescribeStackEvents",
        "cloudformation:ValidateTemplate"
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

5. **Review and Create**
   - Click "Review policy"
   - Name it: `GitHubActionsPipelinePolicy`
   - Click "Create policy"

---

## Step 2: Create AWS Access Keys

### What This Does
Creates long-lived credentials that GitHub Actions will use to deploy the pipeline.

### Instructions

1. **In the same IAM user page**, go to **"Security credentials"** tab

2. **Scroll to "Access keys"** section

3. **Click "Create access key"**

4. **Choose "Application running outside AWS"**

5. **Click "Next"**

6. **Download or copy the keys**:
   - Copy `Access Key ID`
   - Copy `Secret Access Key` (you won't see it again!)

⚠️ **IMPORTANT**: Save these securely. They will be used in GitHub Secrets.

---

## Step 3: Add GitHub Secrets

### What This Does
Stores AWS credentials securely in GitHub so the workflow can authenticate.

### Instructions

1. **Go to your GitHub repository**

2. **Settings → Secrets and variables → Actions**

3. **Click "New repository secret"** and add these three:

   **Secret 1: AWS_ACCESS_KEY_ID**
   - Name: `AWS_ACCESS_KEY_ID`
   - Value: `<your-access-key-id-from-step-2>`

   **Secret 2: AWS_SECRET_ACCESS_KEY**
   - Name: `AWS_SECRET_ACCESS_KEY`
   - Value: `<your-secret-access-key-from-step-2>`

   **Secret 3: AWS_ACCOUNT_ID**
   - Name: `AWS_ACCOUNT_ID`
   - Value: `778277577996`

---

## Step 4: Deploy Infrastructure via GitHub Actions

### What This Does
Triggers the automated deployment workflow which will:
- Deploy the CloudFormation stack
- Create Lambda functions
- Set up Step Functions, EventBridge, SQS, SNS

### Instructions

1. **Push your code to GitHub**
   ```bash
   git push origin feature/sync-upstream-changes
   # or merge to main branch
   ```

2. **GitHub Actions Triggers Automatically**
   - Go to: GitHub repo → "Actions" tab
   - You'll see the workflow: "Deploy Data Pipeline"
   - It will run automatically and show progress

3. **Monitor the Deployment**
   - Click on the workflow run
   - Watch the steps execute
   - Look for any errors in the logs

4. **On Success**
   - All AWS resources will be created
   - You'll receive a confirmation email for the SNS subscription

---

## Step 5: Verify Deployment

### Verify in AWS Console

1. **Check Lambda Functions**
   - Go to: AWS Console → Lambda → Functions
   - Verify you see: `ingest-api-data`, `pipeline-status-notifier`

2. **Check Step Functions**
   - Go to: AWS Console → Step Functions → State machines
   - Verify you see: `country-population-orchestration`

3. **Check CloudFormation Stack**
   - Go to: AWS Console → CloudFormation → Stacks
   - Verify you see: `data-pipeline-orchestration` (Status: CREATE_COMPLETE)

4. **Check EventBridge Rule**
   - Go to: AWS Console → EventBridge → Rules
   - Verify you see: `data-pipeline-schedule-dev`
   - Check if it shows "Enabled"

5. **Check SQS Queue**
   - Go to: AWS Console → SQS → Queues
   - Verify you see: `data-pipeline-notifications-dev`

6. **Check SNS Topic**
   - Go to: AWS Console → SNS → Topics
   - Verify you see: `data-pipeline-notifications-dev`
   - Click into it → check "Subscriptions"
   - You should see an email subscription to `ntvs02011999@gmail.com`

7. **Confirm SNS Subscription (Important!)**
   - Check your email inbox
   - Look for AWS SNS subscription confirmation
   - Click the link to confirm

---

## Step 6: Manual Trigger (Optional)

### Test the Pipeline

After confirming SNS subscription, you can manually trigger the pipeline:

1. **Go to AWS Console → Step Functions**

2. **Click on `country-population-orchestration`**

3. **Click "Start execution"**

4. **Leave input as: `{}`**

5. **Click "Start execution"**

6. **Watch the execution**:
   - You'll see the steps execute (Ingest → Validate → Transform → Notify)
   - CloudWatch Logs will show details
   - You'll receive email notifications on success/failure

### Verify in CloudWatch

1. **Go to: AWS Console → CloudWatch → Log Groups**
2. Check these log groups for any errors:
   - `/aws/lambda/ingest-api-data`
   - `/aws/lambda/pipeline-status-notifier`
   - `/aws/states/country-population-orchestration-dev`

---

## Troubleshooting

### Issue: GitHub Actions Workflow Failed

**Check the logs:**
1. Go to GitHub repo → Actions
2. Click the failed workflow
3. Click the failed step
4. Scroll to see error messages

**Common issues:**
- **Missing AWS Secrets**: Verify all three secrets are added (Step 3)
- **IAM Permission Denied**: Ensure the IAM policy was attached (Step 1)
- **CloudFormation Stack Error**: Check AWS CloudFormation console for error details

### Issue: SNS Email Not Received

1. Check your email spam folder
2. Verify SNS subscription in AWS Console (should show "SubscriptionConfirmed")
3. If not confirmed, check your email for the confirmation link

### Issue: Step Functions Execution Failed

1. **Check Step Functions console:**
   - AWS Console → Step Functions → Executions
   - Click the failed execution
   - Expand the failed step to see error details

2. **Check Lambda logs:**
   - AWS Console → CloudWatch → Log Groups
   - Find `/aws/lambda/ingest-api-data`
   - Search for error messages

3. **Check Glue job logs:**
   - AWS Console → Glue → Jobs
   - Click the job name
   - Check recent runs for error logs

### Issue: S3 Bucket Not Created

The CloudFormation template should create the S3 bucket automatically. If it doesn't exist:
1. Check CloudFormation Stack events for errors
2. Or manually create: `data-pipeline-country-population-<account-id>-dev`

---

## Next Steps

Once everything is verified and working:

1. **Monitor the pipeline** via CloudWatch Logs
2. **Query results** via Athena (check `country_population.countries_curated` table)
3. **Review email notifications** from SNS (one per pipeline run)
4. **Make code changes** to Lambda, Glue scripts and push → automatic re-deployment

---

## Reference Files

- Orchestration Stack: `infra/cloudformation/orchestration.yaml`
- GitHub Actions Workflow: `.github/workflows/deploy-pipeline.yml`
- IAM Policy: `infra/iam/github_actions_policy.json`
- Ingestion Lambda: `lambda_deployment/ingest_api_data.py`
- Notifier Lambda: `lambda_deployment/notify_pipeline_status.py`
- Deploy Script: `infrastructure/scripts/deploy_orchestration.sh`

---

## Questions?

For issues or questions, check:
1. This guide (Step-by-step)
2. AWS CloudFormation stack events
3. CloudWatch Logs
4. GitHub Actions workflow logs
