# AWS Admin Setup Checklist

## Pre-Deployment Checklist

- [ ] Review [ADMIN_PERMISSIONS_GUIDE.md](ADMIN_PERMISSIONS_GUIDE.md)
- [ ] Identify the IAM user who will deploy the pipeline
- [ ] Have AWS Console access with admin privileges

## Step 1: Create Custom Policy

- [ ] Copy policy from `ADMIN_PERMISSIONS_GUIDE.md`
- [ ] Create policy named `DataPipelineDeploymentPolicy`
- [ ] Verify policy created successfully

## Step 2: Attach Policy to User

- [ ] Find the IAM user
- [ ] Attach `DataPipelineDeploymentPolicy`
- [ ] Verify attachment successful

## Step 3: Verify Permissions

- [ ] Run verification command
- [ ] Confirm policy is attached

```bash
aws iam list-attached-user-policies --user-name USERNAME
```

## Step 4: Notify User

Send user the following information:
- ✅ Permissions have been granted
- ✅ Policy name: `DataPipelineDeploymentPolicy`
- ✅ Ready to run deployment script

## User Can Now Run

```bash
./infrastructure/scripts/full_deployment.sh
```

## Post-Deployment Verification

- [ ] Verify S3 bucket created
- [ ] Verify Glue jobs created
- [ ] Verify Lambda functions created
- [ ] Verify Step Functions created

## Troubleshooting

### User still gets AccessDenied

1. Wait 1-2 minutes for policy propagation
2. User should logout and login again
3. Regenerate access keys if needed
4. Check policy attachment again

### Policy creation failed

1. Verify admin account has IAM permissions
2. Check AWS Console for error messages
3. Try CLI command instead of Console

### Verification shows no resources

1. Check if deployment script ran
2. Verify user has AWS credentials configured
3. Check CloudTrail for detailed logs

## Contact & Support

For questions about permissions:
- Reference: [ADMIN_PERMISSIONS_GUIDE.md](ADMIN_PERMISSIONS_GUIDE.md)
- AWS Documentation: https://docs.aws.amazon.com/iam/
