This repository contains a small data pipeline to ingest country data, validate it and transform it into curated parquet.

New additions:
- AWS-ready infra under `infra/` and deployment helper `scripts/deploy_stack.ps1`.

Configuration
- Defaults in `config/config.yml`. Environment variables override config values.

Deploy
- Use `scripts/deploy_stack.ps1` (Windows PowerShell) to create the S3 bucket and IAM role:

```powershell
.\scripts\deploy_stack.ps1 -StackName pipeline-stack -BucketName my-bucket -Region us-east-1
```

Notes
- `utils/s3_helper.upload_to_s3` supports `SKIP_S3_UPLOAD` env var and `ASSUME_ROLE_ARN` for STS assume-role.

