provider "aws" {
  region = "us-east-1"
}

resource "aws_s3_bucket" "data_pipeline" {
  bucket = "data-pipeline-country-population"
  force_destroy = true
}

resource "aws_s3_bucket_versioning" "versioning" {
  bucket = aws_s3_bucket.data_pipeline.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_iam_role" "glue_validation_role" {
  name = "glue-validation-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "glue.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "glue_s3_policy" {
  name = "S3AccessPolicy"
  role = aws_iam_role.glue_validation_role.id
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
          aws_s3_bucket.data_pipeline.arn,
          "${aws_s3_bucket.data_pipeline.arn}/*"
        ]
      }
    ]
  })
}
