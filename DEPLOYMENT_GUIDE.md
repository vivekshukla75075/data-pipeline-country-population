# Data Pipeline Country Population - Complete Setup Guide

## Prerequisites

- AWS Account with permissions to create CloudFormation stacks
- AWS IAM user with proper permissions (see below)
- GitHub repository with this code
- GitHub Secrets configured (see below)

## Quick Start

### 1. Attach IAM Permissions (One-time Setup)

Before first deployment, ensure your IAM user has CloudFormation permissions:

**PowerShell (Windows):**
```powershell
.\attach_iam_policy.ps1
```

**Bash (Linux/Mac):**
```bash
bash attach_iam_policy.sh
```

**Or manually via AWS Console:**
1. Go to AWS IAM → Users → `data-pipeline-country-population`
2. Add inline policy named `CloudFormationDeploymentPolicy`
3. Paste contents of `infra/iam/cloudformation_deployment_policy.json`

### 2. Configure GitHub Secrets

Add these secrets to your GitHub repository (Settings → Secrets and variables → Actions):

```
AWS_ACCESS_KEY_ID         - Your AWS access key
AWS_SECRET_ACCESS_KEY     - Your AWS secret access key
AWS_ACCOUNT_ID            - Your AWS account ID (778277577996)
AWS_REGION                - (Optional) AWS region (default: us-east-1)
```

### 3. Deploy via GitHub Actions

**Build Workflow (Automatic):**
- Triggers on push to `main`, `master`, or `feature/*` branches
- Validates Python code
- Builds Lambda packages
- View at: GitHub → Actions → "1. Build & Validate"

**Deploy Workflow (Manual):**
1. Go to GitHub → Actions → "2. Deploy to AWS"
2. Click "Run workflow"
3. Select environment (`dev`, `staging`, or `prod`)
4. Select AWS region (default: `us-east-1`)
5. Click "Run workflow"

**Destroy Workflow (Manual):**
1. Go to GitHub → Actions → "3. Destroy AWS Resources"
2. Click "Run workflow"
3. Enter stack name: `data-pipeline-orchestration`
4. Select AWS region: `us-east-1`
5. Choose to empty S3 buckets: `true`
6. Enter confirmation token: `DELETE_STACK_CONFIRM`
7. Click "Run workflow"

## Repository Structure

```
.github/workflows/          # GitHub Actions CI/CD
├── 01-build.yml           # Automatic build and validation
├── 02-deploy.yml          # Manual infrastructure deployment
└── 03-destroy.yml         # Manual resource destruction

infra/
├── cloudformation/
│   └── orchestration.yaml # CloudFormation template (all resources)
└── iam/
    └── cloudformation_deployment_policy.json  # IAM permissions

lambda_deployment/          # Lambda function code
├── ingest_api_data.py     # API ingestion function
├── notify_pipeline_status.py  # Notification function
└── *.zip files (auto-generated during build)

docs/
├── CICD_PIPELINE_GUIDE.md  # Detailed CI/CD documentation
├── ARCHITECTURE.md         # System architecture
├── FIX_IAM_PERMISSIONS.md  # IAM setup troubleshooting
└── ...                     # Other documentation

utils/
└── http_utils.py          # HTTP response decompression helper

Ingestion/                  # Local ingestion scripts
Validation/                 # Local validation scripts
Transformation/             # Local transformation scripts
```

## Key Features

### Automated Infrastructure
- **EventBridge** - Scheduled daily API ingestion trigger
- **Step Functions** - Orchestrates data pipeline execution
- **Lambda** - Ingestion and notification functions
- **AWS Glue** - Data validation and transformation jobs
- **S3** - Data lake with medallion architecture (raw/validated/curated)
- **SNS/SQS** - Event notifications
- **IAM Roles** - Properly scoped permissions for each service

### Build Pipeline
- ✅ Python syntax validation
- ✅ CloudFormation template validation
- ✅ Lambda package creation
- ✅ Dependency bundling

### Deployment
- ✅ CloudFormation stack creation/update
- ✅ IAM roles and policies
- ✅ Lambda function deployment
- ✅ Resource configuration
- ✅ Stack output validation

### Cleanup
- ✅ S3 bucket emptying (with versioning support)
- ✅ Stack deletion
- ✅ Resource teardown
- ✅ Cost optimization

## Troubleshooting

### IAM Permission Errors

**Error:** `User is not authorized to perform: cloudformation:ValidateTemplate`

**Solution:**
```powershell
# PowerShell
.\attach_iam_policy.ps1

# Or Bash
bash attach_iam_policy.sh
```

Then retry the deploy workflow.

### GitHub Actions Secrets Not Working

1. Verify secrets exist in Settings → Secrets and variables → Actions
2. Check secret names match exactly (case-sensitive)
3. Make sure you haven't added extra spaces or newlines
4. Re-run the workflow after adding/updating secrets

### Stack Deletion Failed

If S3 buckets prevent stack deletion:

1. Go to GitHub → Actions → "3. Destroy AWS Resources"
2. Set `empty_buckets` to `true`
3. Enter confirmation token: `DELETE_STACK_CONFIRM`
4. Retry destruction

### Deploy Workflow Hangs

1. Check GitHub Actions logs for error messages
2. Verify AWS credentials are still valid
3. Check AWS CloudFormation console for stack status
4. Look for any failed resource creation

## Local Development

### Run Build Locally

```bash
cd lambda_deployment
zip -q ingest_api_data.zip ingest_api_data.py ../utils/http_utils.py
zip -q notify_pipeline_status.zip notify_pipeline_status.py
```

### Run Tests

```bash
python -m pytest tests/
```

### Manual Ingestion Test

```bash
python Ingestion/ingest_data.py
```

## Architecture Overview

```
EventBridge (Daily Schedule)
  ↓
Step Functions (Orchestrator)
  ├→ Lambda (Ingestion)
  │   └→ S3 Raw Zone
  ├→ Glue Job (Validation)
  │   └→ S3 Validated Zone
  ├→ Glue Job (Transformation)
  │   └→ S3 Curated Zone (Parquet)
  └→ Lambda (Notification)
      ├→ SQS Queue
      └→ SNS Topic (Email)
```

## Monitoring

- **AWS CloudFormation** - Check stack status
- **AWS Step Functions** - Monitor execution history
- **AWS Lambda** - View CloudWatch logs
- **AWS S3** - Verify data zones
- **GitHub Actions** - Check workflow runs

## Cost Optimization

- EventBridge triggers daily (configurable)
- Lambda functions are event-driven
- Glue jobs run only on schedule
- S3 versioning enabled for safety

Destroy resources when not in use to avoid ongoing charges:
```
GitHub → Actions → "3. Destroy AWS Resources" → Run workflow
```

## Support

- Check `docs/` folder for detailed guides
- Review GitHub Actions logs for errors
- Check AWS CloudFormation events for resource issues
