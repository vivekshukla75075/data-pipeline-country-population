# Structured Ingestion Data Pipeline Blueprint

## 1. Project goal

Build a new data pipeline from scratch that is similar to the current country-population pipeline, but with support for structured ingestion.

The new pipeline must support:
- ingestion from a REST API and from structured files such as JSON or CSV
- schema-aware validation before data reaches the curated layer
- partitioned storage in S3
- orchestration through AWS Step Functions and Glue
- final analytics access through Athena
- repeatable deployment through CI/CD and CloudFormation

## 2. Success criteria

The project is considered complete only when all of the following are true:
- data can be ingested from at least one structured source
- raw data lands in S3 successfully
- validation rejects bad records or writes clean data only
- intermediate and curated transformations complete without manual fixes
- the final curated data can be queried from Athena
- deployment is repeatable and documented
- IAM permissions are least-privilege and verified

## 3. Recommended architecture

### Components
- Source connectors:
  - REST API ingestion via Lambda or Python script
  - structured file ingestion via S3 upload or scheduled job
- Storage layers:
  - raw/
  - validated/
  - curated/
  - logs/
- Processing:
  - AWS Glue jobs for validation and transformation
  - AWS Step Functions for orchestration
- Access:
  - Athena for querying curated Parquet
  - optional Glue Crawler for table registration

### Target data flow
1. Ingest structured payload into raw S3
2. Validate schema and required columns
3. Write validated Parquet to validated zone
4. Transform to curated Parquet in curated zone
5. Register table metadata in Glue / Athena
6. Query data in Athena

---

## 4. User stories

### A. Design and architecture
- As a data engineer, I want a schema-driven ingestion contract so that structured input is validated before it reaches storage.
- As a platform owner, I want an AWS architecture that is repeatable and easy to redeploy.
- As a stakeholder, I want partitioned data in S3 so that queries are efficient.
- As a developer, I want clear lakehouse-style layers: raw, validated, curated.

### B. Development
- As a developer, I want Python scripts that can run locally and in Glue for ingestion, validation, and transformation.
- As a developer, I want explicit schemas for incoming records so that malformed input fails fast.
- As a developer, I want the transformation layer to preserve partition columns and avoid schema drift.
- As a developer, I want logs and error handling that are easy to troubleshoot.

### C. Deployment
- As a DevOps engineer, I want GitHub Actions to deploy code and infrastructure consistently.
- As a DevOps engineer, I want deployment steps that verify resources before moving to the next stage.
- As a maintainer, I want rollback-safe deployment behavior for Glue scripts and CloudFormation changes.

### D. AWS infrastructure and security
- As a platform owner, I want least-privilege IAM roles for Lambda, Glue, Step Functions, and Athena.
- As a security engineer, I want encryption and bucket policies to be enforced.
- As a data owner, I want curated data to be accessible through Athena without manual permission loops.

---

## 5. Functional requirements

### Ingestion requirements
- ingest either:
  - a JSON array from an API response
  - a structured file uploaded to S3
- write raw data into S3 with metadata such as ingestion timestamp and source
- preserve source file names and ingestion IDs
- support schema versioning per payload

### Validation requirements
- validate required columns and data types
- reject or quarantine invalid rows
- write only valid records to validated layer
- use deterministic output naming and partitioning

### Transformation requirements
- transform validated data into curated Parquet
- partition by a business column such as region or source_date
- preserve a stable output schema for downstream analytics

### Orchestration requirements
- orchestrate ingestion → validation → transformation → Athena registration
- support reruns and retries
- surface failure notifications

### Access requirements
- Athena must be able to read curated Parquet from S3
- Glue catalog metadata must be available for table access

---

## 6. Recommended project structure

```text
project-root/
  scripts/
  src/
    ingestion/
    validation/
    transformation/
  lambda_deployment/
  infra/
    cloudformation/
  tests/
  .github/workflows/
  docs/
```

---

## 7. Step-by-step implementation plan

### Phase 1 — Setup and design

1. Create the GitHub repository and branch strategy.
2. Define the input schema.
3. Decide the S3 layer layout:
   - raw/
   - validated/
   - curated/
   - logs/
4. Choose the ingestion source:
   - API payload
   - file-based structured ingest
5. Create the initial CloudFormation or Terraform plan.

### Phase 2 — Local development baseline

1. Create a Python virtual environment.
2. Add dependencies in requirements.txt.
3. Create local test data samples.
4. Write unit tests for validation logic.
5. Verify local execution of ingestion and transformation scripts.

### Phase 3 — Ingestion implementation

Create a Python ingestion script that writes the raw payload to S3.

```python
import json
import os
from datetime import datetime
import boto3


def ingest_structured_data(bucket_name, source_key, payload, source_name="api"):
    s3 = boto3.client("s3")
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    output_key = f"raw/{source_name}/{timestamp}/{source_key}"

    body = json.dumps(payload, indent=2)
    s3.put_object(Bucket=bucket_name, Key=output_key, Body=body.encode("utf-8"))
    return output_key
```

### Phase 4 — Validation implementation

Create a validation script that checks required columns and writes validated Parquet.

```python
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, LongType, DoubleType

required_columns = ["name", "population", "region"]

schema = StructType([
    StructField("name", StringType(), True),
    StructField("population", LongType(), True),
    StructField("region", StringType(), True),
    StructField("subregion", StringType(), True),
])


def validate_and_write(raw_df, output_path, spark):
    for col in required_columns:
        if col not in raw_df.columns:
            raise ValueError(f"Missing required column: {col}")

    valid_df = raw_df.filter(
        F.col("population").isNotNull() & (F.col("population") > 0)
    )

    valid_df.write.mode("overwrite").format("parquet").partitionBy("region").save(output_path)
    return valid_df
```

### Phase 5 — Transformation implementation

Create a transformation script that reads validated Parquet and writes curated Parquet.

```python
from pyspark.sql import functions as F


def transform_to_curated(validated_df, output_path, spark):
    curated_df = validated_df.select(
        F.col("name").alias("country_name"),
        F.col("region"),
        F.col("subregion"),
        F.col("population"),
        F.current_date().alias("load_date")
    )

    curated_df.write.mode("overwrite").format("parquet").partitionBy("region").save(output_path)
    return curated_df
```

### Phase 6 — Orchestration setup

Use Step Functions to orchestrate ingestion, validation, and transformation.

Important pattern:
- do not assume the next job will start without confirming prior output exists
- verify S3 prefixes or job output before the next task

### Phase 7 — Athena access

1. Create a query results bucket.
2. Configure Athena workgroup result location.
3. Create Glue table metadata.
4. Run a test query.

Example Athena table creation:

```sql
CREATE EXTERNAL TABLE curated_countries (
  country_name string,
  subregion string,
  population bigint,
  load_date date
)
PARTITIONED BY (region string)
STORED AS PARQUET
LOCATION 's3://YOUR-BUCKET/curated/countries/';
```

---

## 8. Deployment plan

### CI/CD steps
1. Push code to GitHub.
2. GitHub Actions runs unit tests.
3. GitHub Actions uploads Glue scripts to S3.
4. GitHub Actions deploys CloudFormation or Terraform.
5. GitHub Actions triggers an end-to-end smoke test.

### Sample GitHub Actions job snippet

```yaml
name: deploy-pipeline
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-region: us-east-1
          role-to-assume: arn:aws:iam::123456789012:role/github-actions-role
      - run: pip install -r requirements.txt
      - run: pytest
      - run: aws s3 cp scripts/ s3://your-bucket/scripts/ --recursive
```

---

## 9. AWS permission policies

### Lambda execution policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-bucket",
        "arn:aws:s3:::your-bucket/*"
      ]
    }
  ]
}
```

### Glue job role policy

```json
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
        "arn:aws:s3:::your-bucket",
        "arn:aws:s3:::your-bucket/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "glue:GetDatabase",
        "glue:GetTable",
        "glue:CreateTable",
        "glue:UpdateTable",
        "glue:CreatePartition"
      ],
      "Resource": "*"
    }
  ]
}
```

### Step Functions execution policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "glue:StartJobRun",
        "glue:GetJobRun",
        "states:StartExecution"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

### Athena access policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "athena:StartQueryExecution",
        "athena:GetQueryExecution",
        "athena:GetQueryResults",
        "athena:GetWorkGroup"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "glue:GetDatabase",
        "glue:GetTable",
        "glue:GetPartitions"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket",
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:s3:::your-bucket",
        "arn:aws:s3:::your-bucket/*"
      ]
    }
  ]
}
```

---

## 10. Lessons learned from the previous project

These are important and should be treated as non-negotiable:
- verify bucket permissions before running Glue jobs
- ensure Glue role has DeleteObject permission for overwrite behavior
- clean stale parquet objects before writing to avoid old data confusion
- when reading partitioned Parquet, use basePath so Spark preserves partition columns
- do not define a column both as a regular column and as a partition column
- verify Athena workgroup result location before first query
- verify schema compatibility between validation and transformation steps
- test the whole flow end-to-end before considering the project complete

---

## 11. Suggested execution checklist

### Design
- [ ] define source schema
- [ ] define target curated schema
- [ ] define S3 layer structure
- [ ] define partition strategy

### Development
- [ ] create project skeleton
- [ ] implement ingestion script
- [ ] implement validation script
- [ ] implement transformation script
- [ ] add unit tests

### Deployment
- [ ] configure GitHub Actions
- [ ] upload scripts to S3
- [ ] deploy CloudFormation/Terraform
- [ ] trigger smoke test

### AWS Infra and security
- [ ] create S3 buckets
- [ ] create IAM roles
- [ ] attach least-privilege policies
- [ ] configure Glue/Athena access
- [ ] verify logs and permissions

---

## 12. Recommended next step

Start with a minimal version first:
1. ingest one structured JSON source
2. validate it
3. write curated Parquet
4. query it in Athena

Once that works, expand to API-based ingestion, retry logic, and notifications.
