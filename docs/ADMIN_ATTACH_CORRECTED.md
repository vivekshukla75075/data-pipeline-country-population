# Corrected: Attach Policy with Proper Account ID

The issue is that the account ID variable needs to be set correctly.

## Step 1: Get Your Account ID First

```bash
aws sts get-caller-identity
```

This will show output like:
```json
{
    "UserId": "AIDAI...",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/data-pipeline-country-population"
}
```

**Copy the Account number** (e.g., `123456789012`)

## Step 2: Attach Policy Using Your Account ID

Replace `YOUR_ACCOUNT_ID` with the actual number from Step 1:

```bash
aws iam attach-user-policy \
  --user-name data-pipeline-country-population \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/DataPipelineDeploymentPolicyupd
```

**Example:**
```bash
aws iam attach-user-policy \
  --user-name data-pipeline-country-population \
  --policy-arn arn:aws:iam::123456789012:policy/DataPipelineDeploymentPolicyupd
```

## Step 3: Verify Attachment

```bash
aws iam list-attached-user-policies --user-name data-pipeline-country-population
```

Should show: `DataPipelineDeploymentPolicyupd` ✅

## Done! 🎉

User can now run:

```bash
./infrastructure/scripts/full_deployment.sh
```
