# CI/CD Pipeline - Build, Deploy & Destroy Guide

This document explains the three-workflow CI/CD pipeline for deploying and managing the data pipeline on AWS.

## Overview

The CI/CD pipeline consists of three independent workflows that can be triggered separately:

```
┌─────────────────┐
│  1. Build       │  ← Runs automatically on every push
│  (Validation)   │     Validates code & CloudFormation
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. Deploy       │  ← Manual trigger (workflow_dispatch)
│ (to AWS)        │     Deploys infrastructure to AWS
└────────┬────────┘
         │
    (Optional)
         │
         ▼
┌─────────────────┐
│ 3. Destroy      │  ← Manual trigger (workflow_dispatch)
│ (from AWS)      │     Removes all AWS resources
└─────────────────┘
```

---

## 1️⃣ Build Workflow (`01-build.yml`)

### What it does
- **Validates** Python syntax for all scripts
- **Validates** CloudFormation YAML template
- **Builds** Lambda deployment packages
- **Verifies** directory structure and dependencies

### When it runs
- ✅ Automatically on every push to `main`, `master`, or any `feature/*` branch
- ✅ On pull requests to `main` or `master`
- ✅ Can be triggered manually anytime

### Duration
~2-3 minutes

### Success indicators
```
✓ Ingestion scripts validated
✓ Validation script validated
✓ Transformation script validated
✓ Notification Lambda validated
✓ CloudFormation YAML syntax valid
✓ All Lambda packages built
✓ Code structure verified
✓ BUILD SUCCESSFUL
```

### Failure causes
- Python syntax errors in any script
- Invalid CloudFormation YAML
- Missing required files
- Directory structure issues

### GitHub Actions UI
```
Repository → Actions → 1. Build & Validate
```

---

## 2️⃣ Deploy Workflow (`02-deploy.yml`)

### What it does
1. **Validates** CloudFormation template against AWS
2. **Builds** Lambda packages with dependencies
3. **Creates/Updates** CloudFormation stack
4. **Deploys** Lambda functions
5. **Provides** stack outputs and verification

### When it runs
- 🔷 **Manual trigger only** - Click "Run workflow" in GitHub Actions
- Recommended: Run AFTER build workflow succeeds

### Input parameters

| Parameter | Options | Default | Description |
|-----------|---------|---------|-------------|
| `environment` | dev, staging, prod | dev | Deployment environment |
| `aws_region` | Any AWS region | us-east-1 | Target AWS region |

### Duration
~5-10 minutes

### How to trigger
```
1. Go to GitHub repository
2. Click "Actions" tab
3. Click "2. Deploy to AWS"
4. Click "Run workflow" button
5. (Optional) Select environment and region
6. Click "Run workflow"
7. Monitor execution in logs
```

### Success indicators
```
✓ CloudFormation template validated
✓ Lambda packages ready
✓ CloudFormation stack deployed
✓ Ingestion Lambda ready
✓ Notifier Lambda ready
✓ Deployment verified
✓ DEPLOYMENT SUCCESSFUL
```

### Stack outputs
After successful deployment, you'll see:
- S3 bucket names
- Lambda function ARNs
- Step Functions state machine ARN
- SQS queue URL
- SNS topic ARN
- EventBridge rule ARN

### Deployed resources
```
data-pipeline-orchestration (CloudFormation stack)
├── Lambda Functions
│   ├── ingest-api-data
│   └── pipeline-status-notifier
├── Step Functions
│   └── country-population-orchestration
├── EventBridge
│   └── data-pipeline-schedule-dev (daily trigger)
├── S3 Buckets
│   ├── data-pipeline-country-population-raw
│   ├── data-pipeline-country-population-validated
│   └── data-pipeline-country-population-curated
├── SQS
│   └── data-pipeline-notifications-dev
├── SNS
│   └── data-pipeline-notifications-dev (with email subscription)
└── IAM Roles
    ├── data-pipeline-execution-role
    ├── data-pipeline-notifier-role
    └── eventbridge-execution-role
```

### Failure causes
- Invalid AWS credentials
- Insufficient IAM permissions
- CloudFormation validation errors
- S3 bucket already exists (name conflict)
- Lambda function creation failed

### Troubleshooting
```
If deployment fails:
1. Check AWS credentials in GitHub Secrets
2. Verify IAM user has required permissions
3. Check CloudFormation stack events in AWS Console
4. Review Lambda function logs in CloudWatch
5. Ensure stack name is unique in region
```

### GitHub Actions UI
```
Repository → Actions → 2. Deploy to AWS
```

---

## 3️⃣ Destroy Workflow (`03-destroy.yml`)

### What it does
1. **Verifies** confirmation token (prevents accidental deletion)
2. **Finds** S3 buckets created by the pipeline
3. **Empties** S3 buckets (removes all objects and versions)
4. **Deletes** CloudFormation stack
5. **Removes** all associated AWS resources
6. **Verifies** deletion and provides summary

### When it runs
- 🔴 **Manual trigger ONLY** - Requires explicit confirmation
- Safety feature: Requires confirmation token `DELETE_STACK_CONFIRM`

### Input parameters

| Parameter | Options | Default | Description |
|-----------|---------|---------|-------------|
| `stack_name` | Any string | data-pipeline-orchestration | CloudFormation stack name |
| `aws_region` | Any AWS region | us-east-1 | Target AWS region |
| `empty_buckets` | true, false | true | Empty S3 buckets before deletion |
| `confirmation_token` | **Must be exact** | DELETE_STACK_CONFIRM | Security confirmation |

### Duration
~5-10 minutes (depends on S3 data volume)

### How to trigger
```
1. Go to GitHub repository
2. Click "Actions" tab
3. Click "3. Destroy AWS Resources"
4. Click "Run workflow" button
5. In "confirmation_token" field, type: DELETE_STACK_CONFIRM (exactly)
6. (Optional) Customize stack_name, region, or bucket emptying
7. Click "Run workflow"
8. Monitor execution (IRREVERSIBLE - be patient)
```

### Success indicators
```
✓ Deletion confirmed
✓ Stack found
✓ Buckets found and emptied
✓ Stack deletion completed
✓ Stack not found (successfully deleted)
✓ CLEANUP SUCCESSFUL
```

### What gets deleted
```
✓ CloudFormation stack
✓ Lambda functions (ingest-api-data, pipeline-status-notifier)
✓ Step Functions state machine
✓ EventBridge schedule rules
✓ SQS notification queue
✓ SNS notification topic
✓ IAM execution roles
✓ S3 bucket contents (data cleaned up)
```

### ⚠️ Important warnings

**This action is IRREVERSIBLE!**
- Once deleted, resources cannot be recovered without redeployment
- Data in S3 buckets will be permanently removed
- No backup is created automatically
- Confirmation token is required to prevent accidents

### Failure causes
- Incorrect confirmation token
- Invalid AWS credentials
- Insufficient IAM permissions
- Stack not found
- CloudFormation stack in invalid state
- S3 bucket locked or access denied

### Troubleshooting
```
If destruction fails:
1. Verify you typed: DELETE_STACK_CONFIRM (exactly)
2. Check AWS credentials
3. Verify IAM user has CloudFormation delete permissions
4. Check if stack exists in the specified region
5. Review CloudFormation stack events in AWS Console
```

### GitHub Actions UI
```
Repository → Actions → 3. Destroy AWS Resources
```

---

## Typical Workflow Example

### Scenario: Deploy pipeline to dev environment, use it, then clean up

**Day 1: Deploy**
```
1. Push code to main branch
2. Wait for Build workflow to succeed (automatic)
3. Go to Actions → 2. Deploy to AWS
4. Click "Run workflow"
5. Select "dev" environment
6. Wait ~10 minutes for deployment
7. Check AWS CloudFormation console
8. Verify S3 buckets and Lambda functions exist
9. Manual trigger of Step Functions state machine (optional)
```

**Day 2-7: Use the pipeline**
```
- Data flows automatically via EventBridge → Step Functions
- Monitor CloudWatch logs
- Query data in Athena/S3
- Make code changes as needed
```

**Day 8: Clean up**
```
1. Go to Actions → 3. Destroy AWS Resources
2. Type "DELETE_STACK_CONFIRM" as confirmation
3. Click "Run workflow"
4. Wait ~5-10 minutes (or longer if S3 has data)
5. Verify cleanup in AWS Console
6. Check billing - resources should be gone
```

---

## GitHub Secrets Configuration

Before running Deploy or Destroy workflows, configure these secrets:

### Go to GitHub:
```
Repository Settings
  → Secrets and variables
    → Actions
      → New repository secret
```

### Add these secrets:

**Option A: Access Keys (simpler)**
```
Secret Name: AWS_ACCESS_KEY_ID
Secret Value: (from AWS IAM user security credentials)

Secret Name: AWS_SECRET_ACCESS_KEY
Secret Value: (from AWS IAM user security credentials)

Secret Name: AWS_ACCOUNT_ID
Secret Value: 778277577996
```

**Option B: OIDC Role (recommended)**
```
Secret Name: AWS_ROLE_ARN
Secret Value: arn:aws:iam::778277577996:role/github-actions-role
```

---

## IAM Permissions Required

The AWS user/role needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:CreateStack",
        "cloudformation:UpdateStack",
        "cloudformation:DeleteStack",
        "cloudformation:DescribeStacks",
        "cloudformation:ValidateTemplate"
      ],
      "Resource": "arn:aws:cloudformation:*:*:stack/data-pipeline*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:CreateFunction",
        "lambda:UpdateFunctionCode",
        "lambda:GetFunction",
        "lambda:DeleteFunction"
      ],
      "Resource": "arn:aws:lambda:*:*:function:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:ListBucket",
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucketVersions",
        "s3:GetObjectVersion",
        "s3:DeleteObjectVersion"
      ],
      "Resource": [
        "arn:aws:s3:::data-pipeline*",
        "arn:aws:s3:::data-pipeline*/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:PutRolePolicy",
        "iam:PassRole"
      ],
      "Resource": "arn:aws:iam::*:role/data-pipeline*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "states:CreateStateMachine",
        "states:UpdateStateMachine",
        "states:DeleteStateMachine"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "events:CreateRule",
        "events:DeleteRule",
        "events:PutTargets",
        "events:RemoveTargets"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sqs:CreateQueue",
        "sqs:DeleteQueue"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sns:CreateTopic",
        "sns:DeleteTopic",
        "sns:Subscribe"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Monitoring & Troubleshooting

### Check workflow status
```
Repository → Actions → [Select workflow] → [Click run]
```

### View workflow logs
```
Click on the workflow run → Click on a step → View full logs
```

### AWS Console verification
```
CloudFormation Console:
  → Stacks
    → Look for "data-pipeline-orchestration"
    → Check "Events" tab for creation/deletion details

Lambda Console:
  → Functions
    → ingest-api-data (should exist after Deploy)
    → pipeline-status-notifier (should exist after Deploy)

S3 Console:
  → Buckets
    → data-pipeline-country-population* (should exist after Deploy)
    → Empty after Destroy

Step Functions Console:
  → State Machines
    → country-population-orchestration (should exist after Deploy)
    → Deleted after Destroy
```

### CloudWatch Logs
```
CloudWatch → Log Groups
  → /aws/lambda/ingest-api-data
  → /aws/lambda/pipeline-status-notifier
  → /aws/states/country-population-orchestration-dev
```

---

## Cost Optimization

### Active deployment costs (daily use)
- **Lambda**: ~$0.20/month (minimal invocations)
- **Step Functions**: ~$0.50/month (daily state transitions)
- **S3**: ~$5-20/month (depends on data volume)
- **CloudWatch Logs**: ~$5-10/month
- **EventBridge**: Free tier (up to 100k events/month)
- **Total**: ~$10-50/month

### Idle deployment costs
- **S3**: $0.23/GB/month (storage only)
- **EventBridge**: Free (inactive rule has no cost)
- **Stopped Lambda**: Free

### Cost savings with Destroy
- Delete when not in use (hourly/weekly/monthly)
- Re-deploy only when needed
- No S3 storage costs when destroyed

### Cost tracking
```
AWS Console → Billing → Cost Explorer
  → Filter by service
  → Group by day
  → Track spending over time
```

---

## Frequently Asked Questions

**Q: Can I deploy to multiple regions?**
A: Yes, run Deploy workflow with different `aws_region` input.

**Q: Can I have multiple environments (dev/staging/prod)?**
A: Yes, use different stack names: `data-pipeline-dev`, `data-pipeline-staging`, `data-pipeline-prod`.

**Q: What if I delete something by mistake?**
A: Redeploy with the Deploy workflow. All resources will be recreated.

**Q: How do I update the code after deployment?**
A: Push code changes to main → Build runs automatically → Deploy workflow to update Lambda functions.

**Q: Can I run workflows without the confirmation token?**
A: No, Destroy workflow requires exact token: `DELETE_STACK_CONFIRM`.

**Q: How long does Destroy take?**
A: 5-10 minutes normally, longer if S3 buckets have large amounts of data.

**Q: What if Destroy times out?**
A: Check AWS CloudFormation console - stack may still be deleting. Wait and check status.

---

## Best Practices

1. ✅ **Always run Build first** - Validate code before deploying
2. ✅ **Test in dev first** - Deploy to dev, verify, then prod
3. ✅ **Review CloudFormation events** - Check AWS Console for details
4. ✅ **Monitor during Deploy** - Watch logs for issues
5. ✅ **Backup data before Destroy** - S3 data will be deleted
6. ✅ **Use confirmation token** - Prevent accidental deletion
7. ✅ **Clean up when done** - Run Destroy to avoid unnecessary costs
8. ✅ **Track deployments** - Keep notes on when you deploy/destroy

---

## Related Documentation

- [AWS Setup Guide](../../docs/AWS_SETUP_GUIDE.md) - Manual setup without CI/CD
- [Architecture](../../docs/ARCHITECTURE.md) - System design
- [Troubleshooting Guide](../../docs/TROUBLESHOOTING_GUIDE.md) - Common issues
- [Workflows README](./) - Workflow documentation

---

**Last Updated**: July 2026
**Version**: 1.0
