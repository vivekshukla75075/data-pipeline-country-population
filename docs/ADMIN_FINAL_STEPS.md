# Final Admin Steps - Policy Already Created

## Current Status

✅ Policy exists: `DataPipelineDeploymentPolicy`  
⏳ Need to: Attach policy to user

---

## Step 1: Attach Policy to User

### Option A: AWS Console (Recommended - Just 3 clicks)

1. Go to: https://console.aws.amazon.com/iam/
2. Click: **Users → data-pipeline-country-population**
3. Click: **Permissions** tab
4. Click: **Add permissions → Attach policies directly**
5. Search: `DataPipelineDeploymentPolicy`
6. Select it ✓
7. Click: **Attach policy**

### Option B: AWS CLI (One command)

```bash
# Get Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Attach policy
aws iam attach-user-policy \
  --user-name data-pipeline-country-population \
  --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/DataPipelineDeploymentPolicy
```

---

## Step 2: Verify

```bash
aws iam list-attached-user-policies --user-name data-pipeline-country-population
```

Should show: `DataPipelineDeploymentPolicy` ✅

---

## Step 3: Tell User

Once attached, send user message:

> "Your permissions have been granted! You can now run `./infrastructure/scripts/full_deployment.sh` to deploy the entire ETL pipeline."

---

## Done! 🎉

User can now automatically create:
- ✅ S3 buckets
- ✅ Glue jobs
- ✅ Lambda functions
- ✅ Step Functions
- ✅ Athena tables

All with one command!
