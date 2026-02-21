# Quick Fix: Just Attach the Existing Policy

Since the policy already exists as `DataPipelineDeploymentPolicyupd`, just attach it to the user:

## One Command:

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text) && \
aws iam attach-user-policy \
  --user-name data-pipeline-country-population \
  --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/DataPipelineDeploymentPolicyupd && \
echo "✅ Policy attached!"
```

## Verify:

```bash
aws iam list-attached-user-policies --user-name data-pipeline-country-population
```

Should show: `DataPipelineDeploymentPolicyupd`

## Done! 🎉

User can now run:

```bash
./infrastructure/scripts/full_deployment.sh
```
