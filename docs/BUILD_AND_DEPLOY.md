# Build and Deploy - Complete Guide

## Overview

New Architecture:
- **Lambda** → Fetch API data → S3 raw
- **Glue Validation** → Process raw → S3 validated → Archive raw
- **Glue Transformation** → Transform → S3 curated (partitioned by region)
- **Athena** → Query curated data

---

## Prerequisites

✅ AWS CLI configured  
✅ Account ID known: `aws sts get-caller-identity --query Account --output text`  
✅ IAM roles exist: `lambda-execution-role`, `glue-validation-role`  
✅ S3 bucket exists: `data-pipeline-country-population`

---

## Step 1: Prepare Files

```bash
# Navigate to project root
cd "f:\All AI projects\data-pipeline-country-population\data-pipeline-country-population"

# Verify structure
ls -la Ingestion/
ls -la Validation/
ls -la Transformation/
ls -la lambda_deployment/
```

Expected:
