# Country Population ETL Pipeline

This repository contains a minimal end-to-end data pipeline for ingesting country population data, validating it, transforming it, and publishing it to AWS storage for analytics.

## End-to-end flow

1. Local development
   - Create and activate a Python virtual environment.
   - Install dependencies: `pip install -r requirements.txt`
   - Run the ingestion job locally: `python Ingestion/ingest_data.py`
   - Run the local validation and transformation checks: `python scripts/local_validate_transform.py`

2. AWS deployment
   - Configure AWS credentials and region.
   - Deploy the core infrastructure from `infra/cloudformation/orchestration.yaml` or use the GitHub Actions workflow in `.github/workflows/02-deploy.yml`.
   - Ensure IAM permissions are available for S3, Glue, Lambda, Step Functions, and CloudWatch.
   - Trigger the pipeline through the deployed workflow or the AWS orchestration resources.

3. Verification
   - Check raw, validated, and curated outputs in S3.
   - Review Glue and Step Functions logs in CloudWatch.
   - Query the curated data using Athena once the AWS resources are available.

## Key folders

- `Ingestion/` - local ingestion entry point
- `Validation/` - validation logic
- `Transformation/` - transformation logic
- `lambda_deployment/` - AWS Lambda-based orchestration helpers
- `infra/` - CloudFormation and Terraform deployment assets
- `tests/` - unit tests

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python Ingestion/ingest_data.py
python scripts/local_validate_transform.py
```

