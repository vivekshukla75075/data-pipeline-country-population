# Troubleshooting: Policy Not Visible

## Problem
- Policy says "already created"
- But can't find it in the search

## Solution

### Step 1: List All Policies to Find It

Run this command to list all policies:

```bash
aws iam list-policies --query 'Policies[?PolicyName==`DataPipelineDeploymentPolicy`]' --output json
```

You should see output like:
```json
[
    {
        "PolicyName": "DataPipelineDeploymentPolicy",
        "PolicyId": "ANPAI23HZ27SI...",
        "Arn": "arn:aws:iam::123456789012:policy/DataPipelineDeploymentPolicy",
        "Path": "/",
        "DefaultVersionId": "v1",
        "AttachmentCount": 0,
        "IsAttachable": true,
        "Description": "",
        "CreateDate": "2024-01-15T10:30:00+00:00",
        "UpdateDate": "2024-01-15T10:30:00+00:00"
    }
]
```

**Copy the `Arn` value** - you'll need it in the next step.

### Step 2: Attach Policy Using ARN (Fastest Method)

Replace `ACCOUNT_ID` with your actual account ID and use this command:

```bash
ACCOUNT_ID=123456789012  # Replace with your actual account ID

aws iam attach-user-policy \
  --user-name data-pipeline-country-population \
  --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/DataPipelineDeploymentPolicy
```

### Step 3: Verify Attachment

```bash
aws iam list-attached-user-policies --user-name data-pipeline-country-population
```

Should show:
```json
{
    "AttachedPolicies": [
        {
            "PolicyName": "DataPipelineDeploymentPolicy",
            "PolicyArn": "arn:aws:iam::123456789012:policy/DataPipelineDeploymentPolicy"
        }
    ]
}
```

---

## If Still Not Working

### Option A: Delete and Recreate Policy

**Warning: Only do this if no one is using the policy**

1. Delete old policy:
```bash
aws iam delete-policy \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/DataPipelineDeploymentPolicy
```

2. Create new policy by copying JSON from `ADMIN_QUICK_POLICY.md`

3. Attach using CLI command above

### Option B: Use Inline Policy Instead

If the managed policy keeps causing issues, use an inline policy:

```bash
cat > /tmp/inline-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:*",
        "glue:*",
        "lambda:*",
        "iam:GetRole",
        "iam:PassRole",
        "states:*",
        "athena:*",
        "logs:*",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam put-user-policy \
  --user-name data-pipeline-country-population \
  --policy-name DataPipelineInlinePolicy \
  --policy-document file:///tmp/inline-policy.json
```

Verify:
```bash
aws iam list-user-policies --user-name data-pipeline-country-population
```

### Option C: Console Not Refreshing

If using AWS Console:

1. **Refresh page** (F5)
2. **Logout and login** again
3. **Clear browser cache**
4. **Try different browser**

---

## Quick Verification Checklist

- [ ] Policy exists: `aws iam get-policy --policy-name DataPipelineDeploymentPolicy`
- [ ] Policy is attachable: `aws iam list-policies | grep DataPipelineDeploymentPolicy`
- [ ] User exists: `aws iam get-user --user-name data-pipeline-country-population`
- [ ] Policy attached: `aws iam list-attached-user-policies --user-name data-pipeline-country-population`

---

## Fastest Solution (Recommended)

Just use the CLI command:

```bash
# Get your account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Attach policy
aws iam attach-user-policy \
  --user-name data-pipeline-country-population \
  --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/DataPipelineDeploymentPolicy

# Verify
aws iam list-attached-user-policies --user-name data-pipeline-country-population
```

Should complete in seconds! ✅
