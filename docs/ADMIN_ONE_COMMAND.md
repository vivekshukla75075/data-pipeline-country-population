# One Command Solution

If the policy exists but won't show in the console, use this ONE command to attach it:

## Copy & Run This:

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text) && \
aws iam attach-user-policy \
  --user-name data-pipeline-country-population \
  --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/DataPipelineDeploymentPolicy && \
echo "✅ Policy attached successfully!"
```

**That's it!** Done in 2 seconds. ✅

---

## Verify It Worked

```bash
aws iam list-attached-user-policies --user-name data-pipeline-country-population
```

Should show: `DataPipelineDeploymentPolicy`

---

## User Can Now Deploy

```bash
./infrastructure/scripts/full_deployment.sh
```
