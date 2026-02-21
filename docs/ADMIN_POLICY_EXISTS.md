# Policy Already Exists - Solutions

The policy `DataPipelineDeploymentPolicy` already exists. Choose one solution below:

---

## Solution 1: Delete Old Policy and Create New One (Recommended)

### Step 1: Delete the existing policy

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws iam delete-policy \
  --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/DataPipelineDeploymentPolicy
```

### Step 2: Create new policy with the JSON from `ADMIN_QUICK_POLICY.md`

1. Go to IAM → Policies → Create policy
2. Click JSON tab
3. Paste the corrected policy JSON
4. Name it: `DataPipelineDeploymentPolicy`
5. Click Create policy

### Step 3: Attach to user

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws iam attach-user-policy \
  --user-name data-pipeline-country-population \
  --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/DataPipelineDeploymentPolicy
```

---

## Solution 2: Use a Different Policy Name

If you don't want to delete the old one, create with a new name:

1. Go to IAM → Policies → Create policy
2. Click JSON tab
3. Paste the corrected policy JSON
4. Name it: `DataPipelineDeploymentPolicy-v2`
5. Click Create policy

Then attach:

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws iam attach-user-policy \
  --user-name data-pipeline-country-population \
  --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/DataPipelineDeploymentPolicy-v2
```

---

## Solution 3: Just Attach Existing Policy (If Permissions Are Correct)

If the old policy has the right permissions, just attach it:

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws iam attach-user-policy \
  --user-name data-pipeline-country-population \
  --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/DataPipelineDeploymentPolicy
```

Check if attached:

```bash
aws iam list-attached-user-policies --user-name data-pipeline-country-population
```

---

## Fastest Fix: One Command

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text) && \
aws iam delete-policy --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/DataPipelineDeploymentPolicy 2>/dev/null; \
echo "Old policy deleted (if existed)"
```

Then create the new one using `ADMIN_QUICK_POLICY.md`

---

## Done! ✅

Once policy is attached to user, run:

```bash
./infrastructure/scripts/full_deployment.sh
```
