param(
    [string]$StackName = "pipeline-stack",
    [string]$BucketName = "my-bucket",
    [string]$Region = "us-east-1"
)

# Deploy CloudFormation stack that creates S3 bucket and IAM role
aws cloudformation deploy --template-file infra/cloudformation/stack.yml --stack-name $StackName --region $Region --parameter-overrides BucketName=$BucketName Environment=prod --capabilities CAPABILITY_NAMED_IAM

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
