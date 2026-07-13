# IAM Policy Attachment Script for Windows PowerShell

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "IAM Policy Attachment Script" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check if AWS CLI is installed
try {
    $awsVersion = aws --version 2>$null
    Write-Host "AWS CLI found: $awsVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ AWS CLI not found. Please install it first." -ForegroundColor Red
    exit 1
}

# Get current AWS user
try {
    $currentUser = aws sts get-caller-identity --query User --output text
    Write-Host "Current AWS User: $currentUser" -ForegroundColor Cyan
} catch {
    Write-Host "✗ Could not get AWS identity. Check your credentials." -ForegroundColor Red
    exit 1
}

Write-Host ""

# Define variables
$IAM_USER = "data-pipeline-country-population"
$POLICY_NAME = "CloudFormationDeploymentPolicy"
$POLICY_FILE = "infra/iam/cloudformation_deployment_policy.json"

# Check if policy file exists
if (-not (Test-Path $POLICY_FILE)) {
    Write-Host "✗ Policy file not found: $POLICY_FILE" -ForegroundColor Red
    exit 1
}

Write-Host "Attaching policy to IAM user: $IAM_USER" -ForegroundColor Yellow
Write-Host "Policy name: $POLICY_NAME" -ForegroundColor Yellow
Write-Host ""

# Read policy content
$policyContent = Get-Content $POLICY_FILE -Raw

# Attach the policy
try {
    aws iam put-user-policy `
        --user-name $IAM_USER `
        --policy-name $POLICY_NAME `
        --policy-document $policyContent
    
    Write-Host "✓ Policy attached successfully" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to attach policy: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Verify the policy was attached
Write-Host "Verifying policy attachment..." -ForegroundColor Cyan
try {
    $policyCheck = aws iam get-user-policy `
        --user-name $IAM_USER `
        --policy-name $POLICY_NAME
    
    Write-Host "✓ Policy verified successfully" -ForegroundColor Green
    Write-Host ""
    
    # Show policy summary
    Write-Host "Policy includes permissions for:" -ForegroundColor Cyan
    Write-Host "  ✓ CloudFormation (create, update, validate, delete stacks)"
    Write-Host "  ✓ Lambda (create, update, delete functions)"
    Write-Host "  ✓ IAM (pass role, create roles, attach policies)"
    Write-Host "  ✓ Step Functions (create, manage state machines)"
    Write-Host "  ✓ EventBridge (create and manage rules)"
    Write-Host "  ✓ SNS/SQS (create topics, send messages)"
    Write-Host "  ✓ Glue (create and run jobs)"
    Write-Host "  ✓ S3 (bucket operations)"
    Write-Host "  ✓ CloudWatch Logs (create log groups, write logs)"
} catch {
    Write-Host "✗ Policy verification failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "✓ IAM policy attachment complete!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. If using GitHub Actions, re-run the deploy workflow"
Write-Host "2. If deploying locally, you can now run: .\deploy_all.ps1"
Write-Host ""
