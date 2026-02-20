# Data Pipeline: Country Population

An AWS-based data pipeline that validates and transforms country population data using AWS Glue and PySpark.

## Architecture

- **Validation**: Reads raw JSON from S3, validates records (population > 0), outputs parquet
- **Transformation**: Reads validated parquet, flattens nested fields, outputs curated parquet partitioned by region
- **Storage**: All data stored in S3 bucket `data-pipeline-country-population`
- **Compute**: AWS Glue for serverless PySpark execution

## Project Structure

```
.
├── config/
│   ├── config.yml
│   └── env/
│       ├── dev.yml
│       └── prod.yml
├── infra/
│   ├── s3_bucket.tf
│   └── iam_role.tf
├── scripts/
│   ├── deploy_stack.ps1
│   ├── ingest_data.py
│   └── utils/
│       ├── s3_helper.py
│       └── validate_population.py
├── data/
│   ├── raw/
│   └── processed/
├── logs/
└── README.md
```

## Configuration

- Defaults in `config/config.yml`. Environment variables override config values.

## Deploy

- Use `scripts/deploy_stack.ps1` (Windows PowerShell) to create the S3 bucket and IAM role:

```powershell
.\scripts\deploy_stack.ps1 -StackName pipeline-stack -BucketName my-bucket -Region us-east-1
```

## Notes

- `utils/s3_helper.upload_to_s3` supports `SKIP_S3_UPLOAD` env var and `ASSUME_ROLE_ARN` for STS assume-role.

