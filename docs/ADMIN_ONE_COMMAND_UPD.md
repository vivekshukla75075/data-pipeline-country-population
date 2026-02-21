# One Command to Attach Policy

Policy created: `DataPipelineDeploymentPolicyupd`

Just run this ONE command to attach it to the user:

## Copy & Run This:

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text) && \
aws iam attach-user-policy \
  --user-name data-pipeline-country-population \
  --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/DataPipelineDeploymentPolicyupd && \
echo "✅ Policy attached successfully!"
```

---

## Verify It Worked

```bash
aws iam list-attached-user-policies --user-name data-pipeline-country-population
```

Should show: `DataPipelineDeploymentPolicyupd`

---

## User Can Now Deploy

```bash
./infrastructure/scripts/full_deployment.sh
```

That's it! 🎉
