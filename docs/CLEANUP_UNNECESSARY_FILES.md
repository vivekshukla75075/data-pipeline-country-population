# Files to Remove - Cleanup Guide

## Unnecessary Files to Delete

### Old Workflow Files
- `.github/workflows/deploy.yml` - Replaced by build_and_deploy.yml
- `.github/workflows/minimal_deploy.yml` - Replaced by build_and_deploy.yml

### Old Documentation (Consolidated into ADMIN_SETUP_GUIDE.md)
- `docs/ADMIN_QUICK_POLICY.md`
- `docs/ADMIN_ATTACH_POLICY.md`
- `docs/ADMIN_ATTACH_CORRECTED.md`
- `docs/ADMIN_ATTACH_ONLY.md`
- `docs/ADMIN_ATTACH_STEP_BY_STEP.md`
- `docs/ADMIN_FINAL_STEPS.md`
- `docs/ADMIN_PERMISSIONS_GUIDE.md`
- `docs/ADMIN_CHECKLIST.md`
- `docs/ADMIN_CHECKLIST_SIMPLE.md`
- `docs/ADMIN_ATTACH_POLICY_UPD.md`
- `docs/ADMIN_ONE_COMMAND_UPD.md`
- `docs/FINAL_SETUP_GUIDE.md`
- `docs/ADMIN_ONE_COMMAND.md`
- `docs/ADMIN_TROUBLESHOOT_POLICY.md`
- `docs/ADMIN_POLICY_EXISTS.md`
- `docs/README_CLEANUP.md`

### Outdated Infrastructure Files
- `infra/terraform/step_functions.tf` - Not needed (using Lambda + CLI)
- `infra/terraform/main.tf` - Consolidated approach
- `infra/terraform/lambda.tf` - Lambda created via script
- `infra/terraform/athena.tf` - Manual setup
- `infra/terraform/glue_catalog.tf` - Glue catalog via script

### Duplicate Scripts
- `lambda_functions/` - Lambda functions created via script instead

## Run Cleanup

```powershell
# Windows PowerShell
@(
  ".github/workflows/deploy.yml",
  ".github/workflows/minimal_deploy.yml",
  "docs/ADMIN_QUICK_POLICY.md",
  "docs/ADMIN_ATTACH_POLICY.md",
  "docs/ADMIN_ATTACH_CORRECTED.md",
  "docs/ADMIN_ATTACH_ONLY.md",
  "docs/ADMIN_ATTACH_STEP_BY_STEP.md",
  "docs/ADMIN_FINAL_STEPS.md",
  "docs/ADMIN_PERMISSIONS_GUIDE.md",
  "docs/ADMIN_CHECKLIST.md",
  "docs/ADMIN_CHECKLIST_SIMPLE.md",
  "docs/ADMIN_ATTACH_POLICY_UPD.md",
  "docs/ADMIN_ONE_COMMAND_UPD.md",
  "docs/FINAL_SETUP_GUIDE.md",
  "docs/ADMIN_ONE_COMMAND.md",
  "docs/ADMIN_TROUBLESHOOT_POLICY.md",
  "docs/ADMIN_POLICY_EXISTS.md",
  "docs/README_CLEANUP.md"
) | ForEach-Object { Remove-Item -Path $_ -Force -ErrorAction SilentlyContinue }

# Remove directories
Remove-Item -Path "infra/terraform" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "lambda_functions" -Recurse -Force -ErrorAction SilentlyContinue

# Commit
git add -A
git commit -m "chore: Remove unnecessary and duplicate files

- Remove old workflow files (deploy.yml, minimal_deploy.yml)
- Remove consolidated documentation files
- Remove terraform infrastructure files (using CLI approach)
- Remove lambda_functions directory (created via script)
- Simplify repository structure"

git push origin feature/sync-upstream-changes
```

## Essential Files to Keep

### Workflows
- `.github/workflows/build_and_deploy.yml` - Single unified workflow

### Documentation
- `docs/README.md` - Project overview
- `docs/ADMIN_SETUP_GUIDE.md` - Admin tasks
- `docs/QUICK_START.md` - Quick start
- `docs/MANUAL_SETUP.md` - Manual setup
- `docs/DEPLOYMENT_READY.md` - Deployment checklist
- `docs/ARCHITECTURE.md` - System design
- `docs/ORCHESTRATION.md` - Pipeline details
- `docs/TROUBLESHOOT_PIPELINE.md` - Troubleshooting

### Infrastructure
- `infrastructure/scripts/deploy_pipeline.sh` - Deployment script
- `infrastructure/scripts/full_deployment.sh` - Full deployment
- `infrastructure/scripts/create_lambda_and_stepfunctions.sh` - Lambda/SF setup

### Source Code
- `src/` or root level: Ingestion, Validation, Transformation
- `utils/` - Utility modules
- `config/` - Configuration files
- `sql/` - Analytics queries
- `tests/` - Unit tests

Done! Repository is now clean and organized. ✅
