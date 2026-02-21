# Step-by-Step: Attach Policy Correctly

## Step 1: Open Terminal/Command Prompt

## Step 2: Get Your AWS Account ID

Run this command and copy the output:

```bash
aws sts get-caller-identity --query Account --output text
```

You'll see a 12-digit number. **Copy it exactly.**

Example output:
```
123456789012
```

## Step 3: Set the Account ID as a Variable

```bash
export ACCOUNT_ID=123456789012
```

Replace `123456789012` with the number from Step 2.

## Step 4: Verify the Variable is Set

```bash
echo $ACCOUNT_ID
```

Should print the account ID.

## Step 5: Attach the Policy

```bash
aws iam attach-user-policy \
  --user-name data-pipeline-country-population \
  --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/DataPipelineDeploymentPolicyupd
```

If successful, no error will appear.

## Step 6: Verify Attachment

```bash
aws iam list-attached-user-policies --user-name data-pipeline-country-population
```

Should show:
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

## ✅ Complete!

User can now run:

```bash
./infrastructure/scripts/full_deployment.sh
```

Everything will deploy automatically! 🚀
