provider "aws" {
  region = "us-east-1"
}

# Reference the existing S3 bucket
data "aws_s3_bucket" "data_pipeline" {
  bucket = "data-pipeline-country-population"
}

# Reference the existing IAM role
data "aws_iam_role" "glue_validation_role" {
  name = "glue-validation-role"
}

# (Optional) If you want to attach a new inline policy to the existing role, you can keep this:
resource "aws_iam_role_policy" "glue_s3_policy" {
  name = "S3AccessPolicy"
  role = data.aws_iam_role.glue_validation_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          data.aws_s3_bucket.data_pipeline.arn,
          "${data.aws_s3_bucket.data_pipeline.arn}/*"
        ]
      }
    ]
  })
}
