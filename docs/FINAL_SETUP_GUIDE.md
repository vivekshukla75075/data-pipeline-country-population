# Final Setup Guide - Attach Policy to User

Policy created: `DataPipelineDeploymentPolicyupd` ✅

## Problem
Policy exists in IAM but not visible when searching in user permissions section.

## Solution: Use AWS CLI (Works 100%)

### Step 1: Get Your Account ID

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo $ACCOUNT_ID
```

### Step 2: Attach Policy Using CLI

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws iam attach-user-policy \
  --user-name data-pipeline-country-population \
  --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/DataPipelineDeploymentPolicyupd
```

If successful, you'll see no error and get your command prompt back.

### Step 3: Verify Attachment

```bash
aws iam list-attached-user-policies --user-name data-pipeline-country-population
```

You should see:
```json
{
    "AttachedPolicies": [
        {
            "PolicyName": "DataPipelineDeploymentPolicyupd",
            "PolicyArn": "arn:aws:iam::123456789012:policy/DataPipelineDeploymentPolicyupd"
        }
    ]
}
```

---

## ✅ Done! Policy is Attached

Now the user can deploy the entire pipeline:

```bash
./infrastructure/scripts/full_deployment.sh
```

---

## Troubleshooting

### If you get "No such policy"

Verify policy exists:
```bash
aws iam list-policies --query 'Policies[?PolicyName==`DataPipelineDeploymentPolicyupd`]'
```

Should show the policy details.

### If you get "User not found"

Verify user exists:
```bash
aws iam get-user --user-name data-pipeline-country-population
```

Should show user details.

### If attachment succeeds but still can't see in console

- Wait 1-2 minutes for console to refresh
- Logout and login again
- Try different browser
- Use CLI to verify (Step 3 above)

---

## Next: Deploy the Pipeline

Once policy is attached, user can run:

```bash
# Make script executable
chmod +x infrastructure/scripts/full_deployment.sh

# Run deployment
./infrastructure/scripts/full_deployment.sh
```

This will automatically create:
- ✅ S3 buckets and directories
- ✅ Glue jobs
- ✅ Lambda functions
- ✅ Step Functions
- ✅ Athena tables

**Everything deploys automatically!** 🚀
