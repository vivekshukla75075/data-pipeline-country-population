# AWS Configuration Guide

## Prerequisites

- AWS Account
- AWS CLI v2+
- IAM User with appropriate permissions
- S3 Bucket: `data-pipeline-country-population`

## Step 1: Create S3 Bucket

```bash
BUCKET_NAME="data-pipeline-country-population"
REGION="us-east-1"

# Create bucket
aws s3 mb s3://$BUCKET_NAME --region $REGION

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket $BUCKET_NAME \
  --versioning-configuration Status=Enabled

# Enable default encryption
aws s3api put-bucket-encryption \
  --bucket $BUCKET_NAME \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# Create folder structure
echo "Creating folder structure..."
aws s3 cp - "s3://$BUCKET_NAME/raw/countries/.keep" <<< ""
aws s3 cp - "s3://$BUCKET_NAME/validated/countries/.keep" <<< ""
aws s3 cp - "s3://$BUCKET_NAME/curated/countries/.keep" <<< ""
aws s3 cp - "s3://$BUCKET_NAME/logs/ingestion_logs/.keep" <<< ""
aws s3 cp - "s3://$BUCKET_NAME/logs/validation_logs/.keep" <<< ""
aws s3 cp - "s3://$BUCKET_NAME/logs/transformation_logs/.keep" <<< ""
aws s3 cp - "s3://$BUCKET_NAME/scripts/.keep" <<< ""

echo "✅ S3 bucket created and configured"
```

## Step 2: Create IAM Roles

### Lambda Execution Role

```bash
# Create role
aws iam create-role \
  --role-name lambda-execution-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Create policy for S3 access
aws iam put-role-policy \
  --role-name lambda-execution-role \
  --policy-name S3AccessPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::data-pipeline-country-population/*",
        "arn:aws:s3:::data-pipeline-country-population"
      ]
    }]
  }'

# Attach CloudWatch Logs policy
aws iam attach-role-policy \
  --role-name lambda-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

echo "✅ Lambda execution role created"
```

### Glue Execution Role

```bash
# Create role
aws iam create-role \
  --role-name glue-validation-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "glue.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Create policy for S3 and Glue
aws iam put-role-policy \
  --role-name glue-validation-role \
  --policy-name GlueAccessPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["s3:*"],
        "Resource": [
          "arn:aws:s3:::data-pipeline-country-population/*",
          "arn:aws:s3:::data-pipeline-country-population"
        ]
      },
      {
        "Effect": "Allow",
        "Action": ["glue:UpdateJob"],
        "Resource": "arn:aws:glue:*:*:job/*"
      }
    ]
  }'

# Attach Glue service policy
aws iam attach-role-policy \
  --role-name glue-validation-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole

echo "✅ Glue execution role created"
```

## Step 3: Create Glue Jobs

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET="data-pipeline-country-population"
REGION="us-east-1"

# Upload scripts first
aws s3 cp Validation/validate_schema.py s3://$BUCKET/scripts/
aws s3 cp Transformation/transform_data.py s3://$BUCKET/scripts/

# Create Validation Job
aws glue create-job \
  --name country-population-validation \
  --role arn:aws:iam::$ACCOUNT_ID:role/glue-validation-role \
  --command Name=glueetl,ScriptLocation=s3://$BUCKET/scripts/validate_schema.py \
  --glue-version 3.0 \
  --worker-type G.1X \
  --number-of-workers 3 \
  --timeout 60 \
  --region $REGION

# Create Transformation Job
aws glue create-job \
  --name country-population-transformation \
  --role arn:aws:iam::$ACCOUNT_ID:role/glue-validation-role \
  --command Name=glueetl,ScriptLocation=s3://$BUCKET/scripts/transform_data.py \
  --glue-version 3.0 \
  --worker-type G.1X \
  --number-of-workers 5 \
  --timeout 60 \
  --region $REGION

echo "✅ Glue jobs created"
```

## Step 4: Create Lambda Function

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"

# Create deployment package
cd lambda_deployment
zip ingest_api_data.zip ingest_api_data.py
cd ..

# Create Lambda function
aws lambda create-function \
  --function-name ingest-api-data \
  --runtime python3.9 \
  --role arn:aws:iam::$ACCOUNT_ID:role/lambda-execution-role \
  --handler ingest_api_data.lambda_handler \
  --zip-file fileb://lambda_deployment/ingest_api_data.zip \
  --timeout 60 \
  --memory-size 256 \
  --region $REGION

echo "✅ Lambda function created"
```

## Step 5: Add IAM User Permissions

```bash
IAM_USER="data-pipeline-country-population"

# Add Lambda update permissions
aws iam put-user-policy \
  --user-name $IAM_USER \
  --policy-name LambdaUpdatePolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": [
        "lambda:UpdateFunctionCode",
        "lambda:GetFunction",
        "lambda:InvokeFunction"
      ],
      "Resource": "arn:aws:lambda:*:*:function:ingest-api-data"
    }]
  }'

# Add Glue job permissions
aws iam put-user-policy \
  --user-name $IAM_USER \
  --policy-name GlueJobPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": [
        "glue:UpdateJob",
        "glue:GetJob",
        "glue:StartJobRun",
        "glue:GetJobRun"
      ],
      "Resource": "arn:aws:glue:*:*:job/*"
    }]
  }'

echo "✅ IAM user permissions added"
```

## Step 6: Create Athena Database and Table

```bash
BUCKET="data-pipeline-country-population"
REGION="us-east-1"

# Create database
aws athena start-query-execution \
  --query-string "CREATE DATABASE IF NOT EXISTS country_population;" \
  --result-configuration OutputLocation=s3://$BUCKET/athena-results/ \
  --region $REGION

sleep 5

# Create table
aws athena start-query-execution \
  --query-string "
  CREATE EXTERNAL TABLE IF NOT EXISTS country_population.countries_curated (
    country_name STRING,
    region STRING,
    subregion STRING,
    population BIGINT,
    area DOUBLE,
    capital_city STRING,
    currency STRING
  )
  PARTITIONED BY (region STRING)
  STORED AS PARQUET
  LOCATION 's3://$BUCKET/curated/countries/'
  " \
  --query-execution-context Database=country_population \
  --result-configuration OutputLocation=s3://$BUCKET/athena-results/ \
  --region $REGION

echo "✅ Athena database and table created"
```

## Step 7: Configure GitHub Actions Secrets

In GitHub repository settings, add these secrets:

