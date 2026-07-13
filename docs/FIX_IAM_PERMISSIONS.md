# Fix IAM Permission Error - CloudFormation Deployment

## Issue
Your IAM user `data-pipeline-country-population` lacks CloudFormation permissions:
```
Error: User is not authorized to perform: cloudformation:ValidateTemplate
```

## Solution: Attach CloudFormation Policy

### Option 1: Using AWS CLI (Recommended)

```bash
# 1. Create inline policy directly on the user
aws iam put-user-policy \
  --user-name data-pipeline-country-population \
  --policy-name CloudFormationDeploymentPolicy \
  --policy-document file://infra/iam/cloudformation_deployment_policy.json

# 2. Verify the policy was attached
aws iam list-user-policies --user-name data-pipeline-country-population

# 3. View the policy content
aws iam get-user-policy \
  --user-name data-pipeline-country-population \
  --policy-name CloudFormationDeploymentPolicy
```

### Option 2: Using AWS Console (Manual)

1. Go to AWS Console → IAM → Users
2. Select `data-pipeline-country-population` user
3. Click "Add permissions" → "Create inline policy"
4. Choose "JSON" tab
5. Copy contents of `infra/iam/cloudformation_deployment_policy.json`
6. Paste into the JSON editor
7. Name it: `CloudFormationDeploymentPolicy`
8. Click "Create policy"

### Option 3: Using PowerShell

```powershell
# First, set your AWS credentials if not already configured
$policyContent = Get-Content "infra/iam/cloudformation_deployment_policy.json" -Raw
aws iam put-user-policy `
  --user-name data-pipeline-country-population `
  --policy-name CloudFormationDeploymentPolicy `
  --policy-document $policyContent
```

## Verify the Fix

After attaching the policy, run the deploy workflow again:

1. Go to GitHub → Your repo → Actions
2. Click "2. Deploy" workflow
3. Click "Run workflow" button
4. Select your environment (dev/staging/prod)
5. Click "Run workflow"

The workflow should now proceed past the CloudFormation validation step.

## Policy Permissions Included

The `cloudformation_deployment_policy.json` includes permissions for:

- ✅ **CloudFormation**: ValidateTemplate, CreateStack, UpdateStack, DescribeStacks
- ✅ **Lambda**: CreateFunction, UpdateFunctionCode, DeleteFunction
- ✅ **IAM**: PassRole, CreateRole, AttachRolePolicy
- ✅ **Step Functions**: CreateStateMachine, UpdateStateMachine, StartExecution
- ✅ **EventBridge**: PutRule, PutTargets, DescribeRule
- ✅ **SNS/SQS**: CreateTopic, SendMessage, Subscribe
- ✅ **Glue**: CreateJob, UpdateJob, StartJobRun
- ✅ **CloudWatch Logs**: CreateLogGroup, PutLogEvents
- ✅ **S3**: Full bucket operations for data-pipeline-* buckets

## Next Steps

1. ✅ Attach the CloudFormation policy to your IAM user
2. Re-run the GitHub Actions deploy workflow
3. Monitor the deployment in AWS CloudFormation console
4. Verify resources are created successfully
5. Test the pipeline manually via Step Functions

## Troubleshooting

If you still get permission errors:

1. **Verify policy was attached:**
   ```bash
   aws iam get-user-policy --user-name data-pipeline-country-population --policy-name CloudFormationDeploymentPolicy
   ```

2. **Check if credentials are correct:**
   ```bash
   aws sts get-caller-identity
   ```

3. **Ensure GitHub Secrets are updated:**
   - Go to GitHub Repo Settings → Secrets and variables → Actions
   - Verify `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` match your user credentials

4. **If error persists, check the specific resource:**
   - Some resources might need additional permissions
   - Check CloudFormation stack events in AWS Console for the exact resource causing issues
