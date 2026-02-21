# Admin Tasks - Simple Checklist

## ✅ What Admin Needs to Do

### 1. Create Policy (5 minutes)

- [ ] Open: https://console.aws.amazon.com/iam/
- [ ] Go to: **Policies → Create policy**
- [ ] Click: **JSON** tab
- [ ] Copy policy from `ADMIN_QUICK_POLICY.md`
- [ ] Paste into editor
- [ ] Name it: `DataPipelineDeploymentPolicy`
- [ ] Click: **Create policy**

### 2. Attach to User (2 minutes)

- [ ] Go to: **Users → data-pipeline-country-population**
- [ ] Click: **Permissions** tab
- [ ] Click: **Add permissions → Attach policies directly**
- [ ] Search: `DataPipelineDeploymentPolicy`
- [ ] Select & Click: **Attach policy**

### 3. Verify (1 minute)

Run this command:

```bash
aws iam list-attached-user-policies --user-name data-pipeline-country-population
```

Should show: `DataPipelineDeploymentPolicy` ✅

### 4. Tell User

Send the user:
> "Permissions granted! You can now run `./infrastructure/scripts/full_deployment.sh`"

---

## Total Time: ~8 minutes

Done! 🎉
