# Attach Existing Policy to User

The policy `DataPipelineDeploymentPolicyupd` has been created. Now you need to attach it to the user.

## Step 1: Get Your AWS Account ID

```bash
aws sts get-caller-identity --query Account --output text
```

Note down the Account ID (looks like: `123456789012`)

---

## Step 2: Attach Policy via AWS Console (Easiest)

1. Go to **IAM → Users → data-pipeline-country-population**
2. Click **Permissions** tab
3. Click **Add permissions → Attach policies directly**
4. Search for: `DataPipelineDeploymentPolicyupd`
5. Select it (checkbox on left)
6. Click **Attach policy** button at bottom right

**Done!** ✅

---

## Step 3: Or Attach via AWS CLI

```bash
# Get your AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Attach the policy
aws iam attach-user-policy \
  --user-name data-pipeline-country-population \
  --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/DataPipelineDeploymentPolicyupd
```

---

## Verify Attachment

Run this command to confirm:

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

## ✅ Complete!

Once attached, the user can run:

```bash
./infrastructure/scripts/full_deployment.sh
```

Everything will deploy automatically!
