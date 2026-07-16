# Quick Reference: Deployment Components

## Complete Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         DATA PIPELINE ARCHITECTURE                               │
└─────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│  EventBridge     │  Triggers pipeline daily (rate: 1 day)
│  Schedule        │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Step Functions State Machine                  │
│              country-population-orchestration-dev                │
└──────────────────────────────────────────────────────────────────┘
         │
         ├─────────────────────────────────────────────────────────┐
         │                                                         │
         ▼                                                         │
    ┌─────────────────┐                                           │
    │   Lambda Fn     │  Fetch country data from REST API         │
    │ ingest-api-data │  ✓ Reads from https://restcountries.com  │
    │    (Python)     │  ✓ Handles retries & timeouts            │
    └────────┬────────┘  ✓ Returns HTTP 200                      │
             │                                                    │
             ▼                                                    │
    ┌──────────────────────┐                                     │
    │     S3 Bucket        │                                     │
    │  data-pipeline-dev   │                                     │
    │                      │                                     │
    │ raw/countries/  ◄────┤─ countries_raw_*.json               │
    │ scripts/            │                                     │
    └──────────────────────┘                                     │
             │                                                    │
             ▼                                                    │
    ┌──────────────────────────────────┐                         │
    │    Glue Job #1                   │                         │
    │ country-population-validation    │                         │
    │ Script: validate_schema.py       │                         │
    │ Workers: G.1X x 3               │                         │
    │ ✓ Validates required fields      │                         │
    │ ✓ Checks data quality            │                         │
    │ ✓ Filters corrupt records        │                         │
    │ ✓ Archives raw files             │                         │
    └──────────┬───────────────────────┘                         │
               │                                                  │
               ▼                                                  │
    ┌──────────────────────┐                                     │
    │   S3 Bucket Zone     │                                     │
    │ validated/countries/ │─ Parquet (partitioned by region)    │
    └──────────────────────┘                                     │
               │                                                  │
               ▼                                                  │
    ┌──────────────────────────────────┐                         │
    │    Glue Job #2                   │                         │
    │ country-population-intermediate  │                         │
    │ Script: intermediate_transform.py│                         │
    │ Workers: G.1X x 3               │                         │
    │ ✓ Flattens nested structures     │                         │
    │ ✓ Extracts capital city array    │                         │
    │ ✓ Converts currencies to JSON    │                         │
    └──────────┬───────────────────────┘                         │
               │                                                  │
               ▼                                                  │
    ┌──────────────────────┐                                     │
    │   S3 Bucket Zone     │                                     │
    │ intermediate/        │─ Parquet (partitioned by region)    │
    │ countries/           │                                     │
    └──────────────────────┘                                     │
               │                                                  │
               ▼                                                  │
    ┌──────────────────────────────────┐                         │
    │    Glue Job #3                   │                         │
    │ country-population-transformation│                         │
    │ Script: transform_data.py        │                         │
    │ Workers: G.1X x 5               │                         │
    │ ✓ Selects curated columns        │                         │
    │ ✓ Adds load_date                 │                         │
    │ ✓ Final data quality checks      │                         │
    └──────────┬───────────────────────┘                         │
               │                                                  │
               ▼                                                  │
    ┌──────────────────────┐                                     │
    │   S3 Bucket Zone     │                                     │
    │ curated/countries/   │─ Parquet (partitioned by region)    │
    └──────────────────────┘                                     │
               │                                                  │
               ├─────────────────────┐                            │
               │                     │                            │
               ▼                     ▼                            │
    ┌────────────────────┐  ┌──────────────────┐                 │
    │  Athena Database   │  │   Lambda Fn      │                 │
    │ country_population │  │  Status Notifier │  Send results   │
    │ countries_curated  │  │   (Python)       │  to SQS/SNS     │
    │ table (External)   │  └─────────┬────────┘                 │
    │ Partitioned by     │            │                          │
    │ region             │            ▼                          │
    └────────────────────┘  ┌────────────────┐                  │
         │                  │   SQS Queue    │                  │
         │                  │  Notifications │                  │
         │                  └────────┬───────┘                  │
         │                           │                          │
         │                           ▼                          │
         │                  ┌──────────────────┐                │
         │                  │   SNS Topic      │                │
         │                  │  Notifications   │                │
         │                  └────────┬─────────┘                │
         │                           │                          │
         │                           ▼                          │
         │                  ┌──────────────────┐                │
         │                  │  Email Alert     │                │
         │                  │ ntvs02011999@... │                │
         │                  └──────────────────┘                │
         │                                                      │
         └──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│              INDEPENDENT TEST INFRASTRUCTURE                      │
│                (PySpark/DataFrame/Spark SQL)                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Glue Test Job: glue-test-job                                   │
│  Script: scripts/glue_test_job.py                               │
│  Input Formats: CSV, Parquet, JSON                              │
│                                                                  │
│  ✓ DataFrame API Tests:                                         │
│    - Column transformations                                     │
│    - Conditional logic (when/otherwise)                         │
│    - Filtering with multiple conditions                         │
│    - String operations (upper, lower, trim)                     │
│                                                                  │
│  ✓ Spark SQL Tests:                                             │
│    - Basic SELECT queries                                       │
│    - Aggregations (COUNT, AVG, MAX, MIN)                        │
│    - GROUP BY with filtering                                    │
│    - Window functions (ROW_NUMBER, PARTITION BY)               │
│                                                                  │
│  Input: s3://data-pipeline-glue-test-{ACCOUNT}/input/          │
│  Output: s3://data-pipeline-glue-test-{ACCOUNT}/output/        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Component Reference Table

| Component | Type | Name | Purpose | Status |
|-----------|------|------|---------|--------|
| **Compute** | | | | |
| Lambda | Ingestion | `ingest-api-data` | Fetch from REST API | ✅ Auto-deployed |
| Lambda | Notification | `pipeline-status-notifier` | Send status alerts | ✅ Auto-deployed |
| Glue Job | ETL #1 | `country-population-validation` | Validate schema & quality | ✅ Auto-created |
| Glue Job | ETL #2 | `country-population-intermediate` | Flatten & transform | ✅ Auto-created |
| Glue Job | ETL #3 | `country-population-transformation` | Curate final dataset | ✅ Auto-created |
| Glue Job | Test | `glue-test-job` | PySpark/SQL validation | ✅ Optional |
| **Storage** | | | | |
| S3 Bucket | Data Lake | `data-pipeline-dev-{ACCOUNT}` | All pipeline data | ✅ Auto-created |
| S3 Zone | Raw | `raw/countries/` | API JSON files | ✅ Auto-created |
| S3 Zone | Validated | `validated/countries/` | Quality-checked Parquet | ✅ Auto-created |
| S3 Zone | Intermediate | `intermediate/countries/` | Flattened Parquet | ✅ Auto-created |
| S3 Zone | Curated | `curated/countries/` | Final Parquet | ✅ Auto-created |
| S3 Zone | Archive | `archive/countries/` | Archived raw JSON | ✅ Auto-created |
| S3 Zone | Scripts | `scripts/` | Glue job Python scripts | ✅ Auto-uploaded |
| S3 Zone | Logs | `logs/` | ETL job logs | ✅ Auto-created |
| **Orchestration** | | | | |
| EventBridge | Schedule | `data-pipeline-schedule-dev` | Daily trigger (rate: 1 day) | ✅ Auto-created |
| Step Functions | State Machine | `country-population-orchestration` | Orchestrate all jobs | ✅ Auto-created |
| **Messaging** | | | | |
| SQS | Queue | `data-pipeline-validation-trigger-dev` | Validation trigger | ✅ Auto-created |
| SQS | Queue | `data-pipeline-notifications-dev` | Status messages | ✅ Auto-created |
| SNS | Topic | `data-pipeline-notifications-dev` | Email alerts | ✅ Auto-created |
| **Analytics** | | | | |
| Athena | Database | `country_population` | Query interface | ⏳ Manual create |
| Athena | Table | `countries_curated` | External table (Parquet) | ⏳ Manual create |
| **IAM Roles** | | | | |
| Role | Lambda | `data-pipeline-ingestion-role-dev` | Ingestion Lambda execution | ✅ Auto-created |
| Role | Lambda | `data-pipeline-notifier-role-dev` | Notification Lambda execution | ✅ Auto-created |
| Role | Glue | `data-pipeline-glue-role-dev` | Glue jobs execution | ✅ Auto-created |
| Role | State Machine | `data-pipeline-statemachine-role-dev` | Step Functions execution | ✅ Auto-created |
| Role | Event | `data-pipeline-eventbridge-role-dev` | EventBridge execution | ✅ Auto-created |
| Role | GitHub Actions | `github-actions-deploy-role` | CI/CD deployment | ⏳ Bootstrapped |

**Legend**: 
- ✅ Auto-deployed/created/uploaded by `02-deploy.yml` workflow
- ⏳ Requires manual setup or optional

## Deployment Workflow (`02-deploy.yml`) Steps

```
1. Checkout code
   ↓
2. Setup Python & dependencies
   ↓
3. Resolve AWS authentication (OIDC or Access Keys)
   ↓
4. Configure AWS credentials
   ↓
5. Validate AWS credentials (sts:GetCallerIdentity)
   ↓
6. Validate CloudFormation template
   ↓
7. Build Lambda packages (zip files)
   ↓
8. Deploy CloudFormation stack (orchestration.yaml)
   ├─ Creates S3 bucket
   ├─ Creates Lambda function stubs
   ├─ Creates Glue roles
   ├─ Creates Step Functions state machine
   ├─ Creates SQS queues
   ├─ Creates SNS topic
   └─ Creates EventBridge rule
   ↓
9. Upload Glue scripts to S3 (NEW)
   ├─ validate_schema.py
   ├─ intermediate_transform.py
   └─ transform_data.py
   ↓
10. Bootstrap S3 folder structure (NEW)
   ├─ raw/countries/.keep
   ├─ validated/countries/.keep
   ├─ intermediate/countries/.keep
   ├─ curated/countries/.keep
   ├─ archive/countries/.keep
   └─ scripts/.keep
   ↓
11. Create/Update Glue jobs (NEW)
   ├─ country-population-validation
   ├─ country-population-intermediate
   └─ country-population-transformation
   ↓
12. Deploy Lambda functions
   ├─ ingest-api-data (with environment variables)
   └─ pipeline-status-notifier (with environment variables)
   ↓
13. Add Lambda invoke permissions (for Step Functions)
   ↓
14. Verify deployment
   ↓
15. ✅ Deployment complete
```

## Key Features Deployed

### ✅ End-to-End Data Pipeline
- API ingestion → Raw S3
- Quality validation → Validated S3
- Data transformation → Intermediate S3
- Data curation → Curated S3
- Query via Athena

### ✅ Automatic Glue Job Creation
- Jobs created automatically during deploy
- Scripts uploaded from repository
- Configuration with S3 paths and arguments
- Retries configured in Step Functions

### ✅ Orchestration with Step Functions
- Linear workflow (no parallel tasks)
- Retry logic (3 attempts with exponential backoff)
- Error handling (Catch states for failures)
- Success/failure notifications

### ✅ Messaging & Notifications
- SQS for asynchronous triggering
- SNS for email alerts
- Status messages on completion
- Error notifications

### ✅ Independent Test Glue Job
- PySpark DataFrame API testing
- Spark SQL validation (aggregations, GROUP BY, window functions)
- Multiple input formats (CSV, Parquet, JSON)
- Comprehensive logging

### ✅ Monitoring & Logging
- CloudWatch Logs for all components
- CloudWatch Metrics for Lambda/Glue/Step Functions
- Log groups created automatically
- 14-day retention policy

### ✅ CI/CD Integration
- GitHub Actions workflow
- OIDC authentication (no secrets stored)
- Automatic deployment on push to main/master
- Manual trigger option with parameters

## Data Flow Summary

```
┌─ Ingestion ────────────────────────────┐
│  API → Lambda → S3 raw                 │
│  Format: JSON                          │
│  Location: raw/countries/*.json        │
└────────────────────────────────────────┘
         │
         ▼
┌─ Validation ───────────────────────────┐
│  Glue: validate_schema.py              │
│  - Check required fields               │
│  - Verify data quality                 │
│  - Archive raw files                   │
│  Format: Parquet (snappy)              │
│  Location: validated/countries/*       │
└────────────────────────────────────────┘
         │
         ▼
┌─ Intermediate Transform ───────────────┐
│  Glue: intermediate_transform.py       │
│  - Flatten nested structures           │
│  - Extract arrays                      │
│  - Type conversions                    │
│  Format: Parquet (snappy)              │
│  Location: intermediate/countries/*    │
└────────────────────────────────────────┘
         │
         ▼
┌─ Final Transformation ─────────────────┐
│  Glue: transform_data.py               │
│  - Select curated columns              │
│  - Add load_date                       │
│  - Final quality checks                │
│  Format: Parquet (snappy)              │
│  Location: curated/countries/*         │
│  Partitioned by: region                │
└────────────────────────────────────────┘
         │
         ▼
┌─ Query & Analysis ─────────────────────┐
│  Athena: country_population.countries_curated
│  - External table (Parquet)            │
│  - Partition pruning                   │
│  - SQL queries on curated data         │
└────────────────────────────────────────┘
```

## Deployment Checklist (Quick)

```bash
# 1. Push to GitHub
git push origin main

# 2. Wait for GitHub Actions workflow (02-deploy.yml) to complete
# OR manually trigger: gh workflow run 02-deploy.yml

# 3. Verify stack deployed
aws cloudformation describe-stacks \
  --stack-name data-pipeline-orchestration \
  --region us-east-1 \
  --query 'Stacks[0].StackStatus'

# 4. Get bucket name
BUCKET=$(aws cloudformation describe-stacks \
  --stack-name data-pipeline-orchestration \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`DataBucketName`].OutputValue' \
  --output text)

# 5. Verify Glue jobs created
aws glue list-jobs --region us-east-1 | grep country-population

# 6. Verify S3 scripts uploaded
aws s3 ls s3://$BUCKET/scripts/

# 7. Test Lambda invocation
aws lambda invoke --function-name ingest-api-data response.json

# 8. Monitor raw data ingestion
aws s3 ls s3://$BUCKET/raw/countries/

# 9. Create Athena table (manual)
# See END_TO_END_DEPLOYMENT_GUIDE.md - Step 6

# ✅ Deployment complete!
```

## Files Modified/Created in This Deployment

```
.github/workflows/
└─ 02-deploy.yml                          ✅ Enhanced with Glue upload & job creation

docs/
├─ END_TO_END_DEPLOYMENT_GUIDE.md          ✨ NEW - Complete deployment guide
├─ GLUE_TEST_JOB.md                       ✅ Existing test job documentation
└─ GLUE_JOB_SETUP.md                      ✅ Existing manual Glue setup

scripts/
├─ glue_test_job.py                       ✅ Enhanced with DataFrame/SQL tests
└─ empty_s3_bucket.py                     ✅ Existing S3 cleanup

infra/cloudformation/
├─ orchestration.yaml                     ✅ Existing main stack
└─ glue-test-job-resources.yaml           ✅ Existing test resources

DEPLOYMENT_VERIFICATION_CHECKLIST.md       ✨ NEW - Verification steps

Validation/
└─ validate_schema.py                     ✅ Existing validation script

Transformation/
├─ intermediate_transform.py              ✅ Existing intermediate script
└─ transform_data.py                      ✅ Existing transformation script
```

---

**Status**: ✅ **DEPLOYMENT READY FOR PRODUCTION**

All components verified, end-to-end data flow tested, independent test infrastructure in place.
