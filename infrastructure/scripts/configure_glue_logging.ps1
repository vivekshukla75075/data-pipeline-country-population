# Configure Glue Job Logging

$Green = "Green"
$Yellow = "Yellow"
$AWS_REGION = "us-east-1"
$BUCKET_NAME = "data-pipeline-country-population"

Write-Host "========== Configuring Glue Job Logging ==========" -ForegroundColor $Yellow

# Create CloudWatch log groups
Write-Host "Creating CloudWatch log groups..." -ForegroundColor $Yellow

$logGroups = @(
    "/aws-glue/jobs/country-population-ingestion",
    "/aws-glue/jobs/country-population-validation",
    "/aws-glue/jobs/country-population-transformation"
)

foreach ($logGroup in $logGroups) {
    try {
        aws logs create-log-group --log-group-name $logGroup --region $AWS_REGION 2>$null
        Write-Host "✓ Created log group: $logGroup" -ForegroundColor $Green
    } catch {
        Write-Host "Log group already exists or error: $logGroup" -ForegroundColor $Yellow
    }
}

Write-Host "✓ Log groups ready" -ForegroundColor $Green

# Get AWS Account ID
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$ROLE_ARN = "arn:aws:iam::${ACCOUNT_ID}:role/glue-validation-role"

Write-Host "Updating Glue jobs with logging configuration..." -ForegroundColor $Yellow

# Update ingestion job
Write-Host "Updating country-population-ingestion..." -ForegroundColor $Yellow
aws glue update-job `
  --name country-population-ingestion `
  --job-command Name=glueetl,ScriptLocation=s3://$BUCKET_NAME/scripts/ingest_data.py `
  --role $ROLE_ARN `
  --glue-version "3.0" `
  --worker-type G.1X `
  --number-of-workers 3 `
  --default-arguments '{
    "--TempDir": "s3://'$BUCKET_NAME'/temp/",
    "--job-bookmark-option": "job-bookmark-enable",
    "--enable-continuous-cloudwatch-log": "true",
    "--continuous-log-logGroup": "/aws-glue/jobs/country-population-ingestion",
    "--continuous-log-logStreamPrefix": "ingestion"
  }' `
  --region $AWS_REGION 2>$null

# Update validation job
Write-Host "Updating country-population-validation..." -ForegroundColor $Yellow
aws glue update-job `
  --name country-population-validation `
  --job-command Name=glueetl,ScriptLocation=s3://$BUCKET_NAME/scripts/validate_schema.py `
  --role $ROLE_ARN `
  --glue-version "3.0" `
  --worker-type G.1X `
  --number-of-workers 3 `
  --default-arguments '{
    "--TempDir": "s3://'$BUCKET_NAME'/temp/",
    "--job-bookmark-option": "job-bookmark-enable",
    "--enable-continuous-cloudwatch-log": "true",
    "--continuous-log-logGroup": "/aws-glue/jobs/country-population-validation",
    "--continuous-log-logStreamPrefix": "validation"
  }' `
  --region $AWS_REGION 2>$null

# Update transformation job
Write-Host "Updating country-population-transformation..." -ForegroundColor $Yellow
aws glue update-job `
  --name country-population-transformation `
  --job-command Name=glueetl,ScriptLocation=s3://$BUCKET_NAME/scripts/transform_data.py `
  --role $ROLE_ARN `
  --glue-version "3.0" `
  --worker-type G.1X `
  --number-of-workers 5 `
  --default-arguments '{
    "--TempDir": "s3://'$BUCKET_NAME'/temp/",
    "--job-bookmark-option": "job-bookmark-enable",
    "--enable-continuous-cloudwatch-log": "true",
    "--continuous-log-logGroup": "/aws-glue/jobs/country-population-transformation",
    "--continuous-log-logStreamPrefix": "transformation"
  }' `
  --region $AWS_REGION 2>$null

Write-Host "✓ Glue jobs updated" -ForegroundColor $Green

Write-Host ""
Write-Host "========== Glue Logging Configuration Complete ==========" -ForegroundColor $Green
Write-Host "Log groups created/verified:"
Write-Host "- /aws-glue/jobs/country-population-ingestion"
Write-Host "- /aws-glue/jobs/country-population-validation"
Write-Host "- /aws-glue/jobs/country-population-transformation"
Write-Host ""
Write-Host "View logs at: https://console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION#logStream:"
Write-Host "============================================================" -ForegroundColor $Green
