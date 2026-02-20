# AWS Setup Instructions

## Prerequisites

Your AWS IAM user needs the following permissions:
- `s3:GetObject`
- `s3:PutObject`
- `s3:ListBucket`

Your AWS administrator needs to create:
- S3 bucket for data storage
- IAM role for Glue jobs

## Manual Setup Steps

### 1. Create S3 Bucket (Admin Only)

Replace `ACCOUNT_ID` with your actual AWS account ID:

```bash
aws s3api create-bucket \
  --bucket data-pipeline-bucket-ACCOUNT_ID-dev \
  --region us-east-1
```

Or use AWS Console:
1. Go to S3 service
2. Click "Create Bucket"
3. Name: `data-pipeline-bucket-ACCOUNT_ID-dev`
4. Region: `us-east-1`
5. Click "Create"

### 2. Enable Versioning (Admin Only)

```bash
aws s3api put-bucket-versioning \
  --bucket data-pipeline-bucket-ACCOUNT_ID-dev \
  --versioning-configuration Status=Enabled
```

### 3. Create IAM Role for Glue (Admin Only)

```bash
# Create trust policy file
cat > trust-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "glue.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create role
aws iam create-role \
  --role-name glue-validation-role \
  --assume-role-policy-document file://trust-policy.json

# Create and attach S3 policy
cat > s3-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::data-pipeline-bucket-ACCOUNT_ID-dev",
        "arn:aws:s3:::data-pipeline-bucket-ACCOUNT_ID-dev/*"
      ]
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name glue-validation-role \
  --policy-name S3AccessPolicy \
  --policy-document file://s3-policy.json
```

### 4. Grant User S3 Permissions (Admin Only)

Attach this policy to the IAM user:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:s3:::data-pipeline-bucket-*",
        "arn:aws:s3:::data-pipeline-bucket-*/*"
      ]
    }
  ]
}
```

## Deployment

Once the bucket and IAM role are created, the GitHub Actions workflow will:
1. Verify the bucket exists
2. Upload validation scripts
3. Upload transformation scripts
4. Upload IAM policies

Push to the feature branch to trigger deployment:

```bash
git push origin feature/sync-upstream-changes
```

## Troubleshooting

**Error: AccessDenied on CreateBucket**
- Solution: Ask AWS admin to create bucket first

**Error: Bucket does not exist**
- Solution: Verify bucket name matches your account ID and environment

**Error: AccessDenied on PutObject**
- Solution: Verify IAM user has S3:PutObject permission
