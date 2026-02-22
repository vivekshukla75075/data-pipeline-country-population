# Development Guide - ETL Pipeline

## Overview

This document provides comprehensive guidance for developing and working with the Country Population ETL Pipeline.

## Table of Contents

1. [Environment Setup](#environment-setup)
2. [Development Workflow](#development-workflow)
3. [Local Testing](#local-testing)
4. [Code Structure](#code-structure)
5. [Best Practices](#best-practices)
6. [Debugging](#debugging)

## Environment Setup

### Prerequisites

- Python 3.9+
- AWS CLI configured with credentials
- Git
- Docker (optional, for local Glue testing)

### Local Setup

```bash
# Clone repository
git clone <repo-url>
cd data-pipeline-country-population

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure AWS credentials
aws configure
```

### AWS Credentials

```bash
# Set environment variables
export AWS_ACCESS_KEY_ID=<your-key>
export AWS_SECRET_ACCESS_KEY=<your-secret>
export AWS_DEFAULT_REGION=us-east-1
```

## Development Workflow

### 1. Feature Development

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes to files
# Test locally
# Commit changes
git add .
git commit -m "feat: Description of changes"

# Push to remote
git push origin feature/your-feature-name
```

### 2. Testing Changes Locally

```bash
# Test Lambda function locally
python lambda_deployment/ingest_api_data.py

# Test Validation script locally
python Validation/validate_schema.py

# Test Transformation script locally
python Transformation/transform_data.py
```

### 3. GitHub Actions Deployment

When you push to `feature/sync-upstream-changes`:
1. GitHub Actions validates Python syntax
2. Builds Lambda package
3. Deploys to AWS
4. Runs tests

Check status: **GitHub → Actions → Build and Deploy**

## Local Testing

### Test Lambda Function

```python
# Test ingestion locally
import json
from lambda_deployment.ingest_api_data import lambda_handler

# Mock Lambda context
class MockContext:
    function_name = "ingest-api-data"
    aws_request_id = "test-id"

response = lambda_handler({}, MockContext())
print(json.dumps(response, indent=2))
```

### Test Validation Job

```bash
# Run validation locally (without Glue)
cd Validation
python validate_schema.py

# Output:
# - Reads from S3
# - Processes data
# - Writes logs to S3
```

### Test with Sample Data

```bash
# Create sample JSON file
cat > sample_data.json << 'EOF'
[
  {"name": {"common": "United States"}, "region": "Americas", "population": 331900000},
  {"name": {"common": "India"}, "region": "Asia", "population": 1380004385}
]
EOF

# Upload to S3
aws s3 cp sample_data.json s3://data-pipeline-country-population/raw/countries/
```

## Code Structure

### Lambda Function

**File**: `lambda_deployment/ingest_api_data.py`

