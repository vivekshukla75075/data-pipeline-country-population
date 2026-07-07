# Architecture Documentation

## System Overview

This is a production-ready, serverless ETL data pipeline that ingests country population data from the REST Countries API, processes it through validation and transformation stages, and makes it queryable through AWS Athena. The pipeline follows best practices with a medallion architecture pattern (Raw → Validated → Curated zones) and leverages AWS managed services for scalability and reliability.

## High-Level Architecture

```
┌─────────────────┐
│  REST Countries │
│      API        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────────────────┐
│  AWS Lambda     │      │    AWS Step Functions   │
│  (Ingestion)    │◄─────┤    (Orchestration)      │
└────────┬────────┘      └─────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│              Amazon S3 Bucket                    │
│   data-pipeline-country-population              │
│                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────┐│
│  │  Raw Zone   │→ │ Validated    │→ │Curated  ││
│  │  (JSON)     │  │ Zone         │  │Zone     ││
│  │             │  │ (Parquet)    │  │(Parquet)││
│  └─────────────┘  └──────────────┘  └─────────┘│
└────────┬────────────────┬────────────────┬──────┘
         │                │                │
         │                ▼                ▼
         │      ┌─────────────────┐  ┌──────────┐
         │      │   AWS Glue      │  │   AWS    │
         │      │   Jobs          │  │  Glue    │
         │      │ • Validation    │  │  Catalog │
         │      │ • Transformation│  └────┬─────┘
         │      └─────────────────┘       │
         │                                 ▼
         │                        ┌──────────────┐
         └───────────────────────►│ AWS Athena   │
                                  │ (SQL Queries)│
                                  └──────────────┘
```

## Architecture Components

### 1. Ingestion Layer

**AWS Lambda Function (`ingest_api_data`)**
- **Purpose**: Fetch country data from REST Countries API and store in S3 Raw Zone
- **Location**: `lambda_functions/orchestration/ingest_api_data.py`
- **API Endpoint**: `https://restcountries.com/v3.1/all`
- **Output**: JSON files in `s3://data-pipeline-country-population/raw/countries/`
- **Features**:
  - HTTP request with custom User-Agent header
  - 30-second timeout
  - Error handling with detailed logging
  - Timestamped output files (`countries_raw_YYYYMMDD_HHMMSS.json`)

**Alternative Script (`Ingestion/ingest_data.py`)**
- Glue-compatible ingestion script with multiple fallback methods:
  - Primary: urllib HTTP client
  - Fallback: requests library
  - Emergency: Sample data for testing
- Can run as standalone script or AWS Glue job

### 2. Validation Layer

**AWS Glue Job (`country-population-validation`)**
- **Purpose**: Validate raw JSON data and convert to Parquet format
- **Script**: `Validation/validate_schema.py`
- **Input**: `s3://.../raw/countries/*.json`
- **Output**: `s3://.../validated/countries/*.parquet`
- **Worker Type**: G.1X (General purpose, 1 DPU)
- **Number of Workers**: 3
- **Validation Rules**:
  - Required fields: `name`, `population`, `region`
  - Population must be > 0
  - No null values allowed in required fields
  - Schema enforcement and type checking
- **Processing**:
  - Reads JSON (handles multiline and array formats)
  - Flattens nested name structure (common, official)
  - Filters invalid records
  - Archives raw data after processing
  - Writes validated data as Parquet

### 3. Transformation Layer

**AWS Glue Job (`country-population-transformation`)**
- **Purpose**: Transform validated data into analytics-ready curated format
- **Script**: `Transformation/transform_data.py`
- **Input**: `s3://.../validated/countries/*.parquet`
- **Output**: `s3://.../curated/countries/region=*/`
- **Worker Type**: G.1X
- **Number of Workers**: 5
- **Transformations**:
  - Flattens nested JSON structures (currencies, capital, name)
  - Normalizes data types
  - Calculates derived fields (population density)
  - Handles missing/null values
  - Partitions by region for query optimization
- **Output Format**:
  - Parquet with Snappy compression
  - Partitioned by `region` (Africa, Americas, Asia, Europe, Oceania, Antarctic)
  - Overwrite mode for idempotency

### 4. Orchestration Layer

**AWS Step Functions State Machine**
- **Name**: `country-population-etl-pipeline`
- **Definition**: `infrastructure/terraform/step_functions.tf`
- **Workflow Stages**:
  1. **IngestData**: Trigger Lambda to fetch API data
  2. **ValidateData**: Run Glue validation job
  3. **TransformData**: Run Glue transformation job
  4. **UpdateDataCatalog**: Register tables in Glue Data Catalog
  5. **QueryAthena**: Execute sample analytical queries
  6. **ErrorHandler**: Handle failures (retry logic, notifications)
- **Features**:
  - State-based error handling
  - Catch blocks for each stage
  - Success/Failure terminal states
  - Integration with Lambda and Glue

### 5. Storage Layer

**Amazon S3 Bucket**: `data-pipeline-country-population`

**Data Zones** (Medallion Architecture):

1. **Raw Zone** (`raw/countries/`)
   - Format: JSON
   - Source: Direct API responses
   - Retention: Archived after validation
   - Purpose: Immutable source of truth

2. **Validated Zone** (`validated/countries/`)
   - Format: Parquet
   - Schema: Enforced and validated
   - Cleaned: Invalid records filtered
   - Purpose: Clean, typed data for processing

3. **Curated Zone** (`curated/countries/region=*/`)
   - Format: Parquet (Snappy compressed)
   - Partitioning: By region
   - Optimized: For analytical queries
   - Purpose: Business-ready analytics datasets

4. **Scripts Zone** (`scripts/`)
   - Contains: Python scripts for Glue jobs
   - Uploaded: During deployment

5. **Policies Zone** (`policies/`)
   - Contains: IAM policy documents

### 6. Analytics Layer

**AWS Glue Data Catalog**
- Database: `country_population`
- Table: `countries_curated`
- Partitions: Automatically discovered by region
- Schema: Inferred from Parquet metadata

**AWS Athena**
- Serverless SQL query engine
- Queries curated Parquet data in S3
- Sample queries in `sql/analytics/`:
  - `population_by_region.sql`: Aggregate statistics by region
  - `top_countries_by_population.sql`: Ranking queries

## Data Flow

### End-to-End Pipeline Execution

```
1. TRIGGER
   └─► Step Functions State Machine starts
   
2. INGESTION
   └─► Lambda fetches from REST Countries API
       └─► Writes JSON to s3://.../raw/countries/
   
3. VALIDATION
   └─► Glue Job reads raw JSON
       └─► Validates schema and data quality
       └─► Writes Parquet to s3://.../validated/countries/
       └─► Archives raw JSON
   
4. TRANSFORMATION
   └─► Glue Job reads validated Parquet
       └─► Flattens and enriches data
       └─► Writes partitioned Parquet to s3://.../curated/countries/region=*/
   
5. CATALOG
   └─► Update Glue Data Catalog with new partitions
   
6. ANALYTICS
   └─► Athena queries curated data
       └─► Returns analytical insights
```

### Data Schema Evolution

**Raw Data** (JSON):
```json
{
  "name": {
    "common": "United States",
    "official": "United States of America"
  },
  "region": "Americas",
  "subregion": "Northern America",
  "population": 331900000,
  "area": 9833517,
  "capital": ["Washington, D.C."],
  "currencies": {"USD": {"name": "US Dollar"}}
}
```

**Validated Data** (Parquet):
- Schema enforced
- Type validation
- Required fields present
- Null handling

**Curated Data** (Parquet):
```
Columns:
- country_name (string)
- official_name (string)
- region (string) [partition key]
- subregion (string)
- population (long)
- area (double)
- capital (string)
- currency_code (string)
- currency_name (string)
- population_density (double) [derived]
```

## Technology Stack

### AWS Services
- **AWS Lambda**: Serverless ingestion function
- **AWS Glue**: Managed ETL service (PySpark)
- **Amazon S3**: Object storage (data lake)
- **AWS Glue Data Catalog**: Metadata repository
- **AWS Athena**: Serverless SQL analytics
- **AWS Step Functions**: Workflow orchestration
- **AWS CloudWatch**: Logging and monitoring
- **AWS IAM**: Access control

### Programming Languages & Frameworks
- **Python 3.x**: Primary language
- **PySpark**: Data processing framework
- **SQL**: Analytical queries
- **Terraform**: Infrastructure as Code (IaC)
- **YAML**: Configuration files
- **Bash/PowerShell**: Deployment scripts

## Project Structure

```
data-pipeline-country-population/
│
├── config/                          # Configuration files
│   ├── config.yaml                  # Main configuration
│   └── __init__.py
│
├── Ingestion/                       # Ingestion module
│   ├── ingest_data.py              # Glue-compatible ingestion script
│   └── __init__.py
│
├── Validation/                      # Validation module
│   ├── validate_schema.py          # Schema validation Glue job
│   ├── test_validate_schema.py     # Unit tests
│   └── __init__.py
│
├── Transformation/                  # Transformation module
│   ├── transform_data.py           # Data transformation Glue job
│   └── __init__.py
│
├── lambda_functions/               # Lambda function code
│   ├── orchestration/
│   │   └── ingest_api_data.py     # API ingestion Lambda
│   └── ingestion/
│
├── infrastructure/                 # Infrastructure as Code
│   ├── terraform/
│   │   └── step_functions.tf      # Step Functions definition
│   └── scripts/
│       ├── deploy_pipeline.sh     # Main deployment script
│       ├── setup_glue_jobs.sh     # Glue job setup
│       └── configure_glue_logging.sh
│
├── utils/                          # Utility modules
│   ├── logger.py                  # Logging utilities
│   ├── s3_helper.py               # S3 helper functions
│   └── s3_utils.py                # S3 utilities
│
├── sql/                           # SQL queries
│   └── analytics/
│       ├── population_by_region.sql
│       └── top_countries_by_population.sql
│
├── docs/                          # Documentation
│   ├── ARCHITECTURE.md            # This file
│   ├── DEPLOYMENT.md              # Deployment guide
│   ├── TROUBLESHOOTING_GUIDE.md   # Troubleshooting
│   └── [other docs]
│
├── output/                        # Local output (for testing)
│   ├── raw/
│   ├── validated/
│   └── curated/
│
└── README.md                      # Project overview
```

## Configuration

### Main Configuration File (`config/config.yaml`)

```yaml
application:
  name: "data-pipeline-country-population"
  version: "1.0.0"
  environment: "dev"

aws:
  region: "us-east-1"
  s3_bucket: "data-pipeline-country-population"
  glue_job_role: "glue-validation-role"

s3:
  raw_zone: "raw/countries"
  validated_zone: "validated/countries"
  curated_zone: "curated/countries"

ingestion:
  api:
    url: "https://restcountries.com/v3.1/all"
    timeout: 30
    retries: 3

validation:
  required_fields:
    - "name"
    - "population"
    - "region"
  rules:
    population_min: 0

transformation:
  output_format: "parquet"
  partition_by: "region"
  compression: "snappy"

glue_jobs:
  validation:
    name: "country-population-validation"
    worker_type: "G.1X"
    num_workers: 3
  transformation:
    name: "country-population-transformation"
    worker_type: "G.1X"
    num_workers: 5
```

## Security & IAM

### IAM Roles

1. **Lambda Execution Role**
   - S3 read/write permissions
   - CloudWatch Logs write
   - Step Functions invoke

2. **Glue Job Role** (`glue-validation-role`)
   - S3 full access (to data bucket)
   - Glue service permissions
   - CloudWatch Logs write
   - Glue Data Catalog access

3. **Step Functions Execution Role**
   - Lambda invoke permissions
   - Glue StartJobRun permissions
   - CloudWatch Logs write

### Security Best Practices
- IAM roles follow least privilege principle
- S3 bucket encryption at rest
- Data in transit encrypted (HTTPS)
- No hardcoded credentials
- Separate roles per service

## Monitoring & Logging

### CloudWatch Logs
- Lambda execution logs: `/aws/lambda/ingest_api_data`
- Glue job logs: `/aws-glue/jobs/[job-name]`
- Step Functions execution logs

### Metrics
- Lambda invocation count, duration, errors
- Glue job run status, DPU hours
- Step Functions execution success rate
- S3 object counts per zone

### Observability
- Detailed logging at each pipeline stage
- Error tracking with stack traces
- Execution timestamps for debugging
- Data quality metrics (records processed, filtered)

## Scalability & Performance

### Design Considerations
- **Serverless**: Auto-scales with workload
- **Partitioning**: Region-based for query optimization
- **Compression**: Snappy for fast read/write
- **Parquet Format**: Columnar storage for analytics
- **Worker Scaling**: Configurable Glue workers

### Performance Optimizations
- Parallel processing with PySpark
- S3 lifecycle policies for cost optimization
- Glue catalog for metadata caching
- Athena query result caching

## Cost Optimization

- **Lambda**: Pay per invocation (millions free tier)
- **Glue**: Pay per DPU-hour (only when jobs run)
- **S3**: Standard storage, lifecycle policies to archive old raw data
- **Athena**: Pay per TB scanned (Parquet + compression reduces cost)
- **Step Functions**: Pay per state transition

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

**Quick Start**:
1. Configure AWS credentials
2. Run: `./infrastructure/scripts/deploy_pipeline.sh`
3. Trigger: Execute Step Functions state machine

## Future Enhancements

- [ ] Real-time ingestion with Kinesis
- [ ] Data quality dashboard (QuickSight)
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Incremental processing (change data capture)
- [ ] Data versioning with Delta Lake
- [ ] Cost anomaly detection
- [ ] SNS notifications for failures
- [ ] API Gateway for on-demand queries

## References

- AWS Glue Developer Guide: https://docs.aws.amazon.com/glue/
- AWS Step Functions: https://docs.aws.amazon.com/step-functions/
- PySpark Documentation: https://spark.apache.org/docs/latest/api/python/
- REST Countries API: https://restcountries.com/

---

**Last Updated**: February 23, 2026  
**Version**: 1.0.0  
**Maintainer**: Data Engineering Team

