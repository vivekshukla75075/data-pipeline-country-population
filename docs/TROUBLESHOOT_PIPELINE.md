# Troubleshooting: Pipeline Execution Guide

## Current Status

✅ Step Functions execution succeeded  
❌ Athena query failed (`Query failed with status: FAILED`)

## Solutions

### Step 1: Upload Sample Data First

The pipeline needs raw data to process. Upload sample country data:

```bash
# Create sample data
cat > /tmp/countries.json <<'EOF'
[
  {
    "name": {"common": "United States"},
    "region": "Americas",
    "subregion": "Northern America",
    "population": 331900000,
    "area": 9833517,
    "capital": ["Washington, D.C."],
    "currencies": {"USD": {"name": "US Dollar"}}
  },
  {
    "name": {"common": "India"},
    "region": "Asia",
    "subregion": "South Asia",
    "population": 1380004385,
    "area": 3287263,
    "capital": ["New Delhi"],
    "currencies": {"INR": {"name": "Indian Rupee"}}
  },
  {
    "name": {"common": "Germany"},
    "region": "Europe",
    "subregion": "Western Europe",
    "population": 83370000,
    "area": 357022,
    "capital": ["Berlin"],
    "currencies": {"EUR": {"name": "Euro"}}
  }
]
EOF

# Upload to S3
aws s3 cp /tmp/countries.json s3://data-pipeline-country-population/raw/countries/countries_raw.json

echo "✅ Sample data uploaded"
```

### Step 2: Create Glue Data Catalog Table

Run Athena query to create the curated table:

```bash
aws athena start-query-execution \
  --query-string "CREATE EXTERNAL TABLE IF NOT EXISTS country_population.countries_curated (
    country_name STRING,
    region STRING,
    subregion STRING,
    population BIGINT,
    area DOUBLE,
    capital_city STRING,
    currency STRING
  )
  PARTITIONED BY (region STRING)
  STORED AS PARQUET
  LOCATION 's3://data-pipeline-country-population/curated/countries/'" \
  --query-execution-context Database=country_population \
  --result-configuration OutputLocation=s3://data-pipeline-country-population/athena-results/ \
  --region us-east-1
```

### Step 3: Verify Glue Database

```bash
# Check if database exists
aws glue get-database --name country_population --region us-east-1
```

If it doesn't exist, create it:

```bash
aws glue create-database \
  --database-input Name=country_population,Description="Country population data" \
  --region us-east-1
```

### Step 4: Run Pipeline Again

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:$ACCOUNT_ID:stateMachine:country-population-etl-pipeline \
  --input '{}' \
  --region us-east-1
```

### Step 5: Monitor Execution

```bash
aws stepfunctions describe-execution \
  --execution-arn <EXECUTION_ARN> \
  --region us-east-1
```

### Step 6: Query Results in Athena

Once pipeline succeeds, query the data:

```bash
aws athena start-query-execution \
  --query-string "SELECT region, SUM(population) AS total_population, COUNT(*) AS country_count FROM country_population.countries_curated GROUP BY region ORDER BY total_population DESC" \
  --query-execution-context Database=country_population \
  --result-configuration OutputLocation=s3://data-pipeline-country-population/athena-results/ \
  --region us-east-1
```

---

## Quick Checklist

- [ ] Sample data uploaded to `s3://data-pipeline-country-population/raw/countries/countries_raw.json`
- [ ] Glue database `country_population` created
- [ ] Glue table `countries_curated` created
- [ ] Lambda functions have Athena + S3 permissions
- [ ] Step Functions role has Lambda invoke permissions
- [ ] Pipeline executed successfully

---

## Expected Output

After successful execution:
- ✅ Raw data ingested from S3
- ✅ Data validated (population > 0)
- ✅ Data transformed and partitioned by region
- ✅ Glue Data Catalog updated
- ✅ Athena queries executed
- ✅ Results available in Athena

---

## Full End-to-End Command Sequence

```bash
# 1. Create database
aws glue create-database \
  --database-input Name=country_population \
  --region us-east-1

# 2. Upload data
aws s3 cp /tmp/countries.json s3://data-pipeline-country-population/raw/countries/countries_raw.json

# 3. Create Athena table
aws athena start-query-execution \
  --query-string "CREATE EXTERNAL TABLE IF NOT EXISTS country_population.countries_curated (country_name STRING, region STRING, subregion STRING, population BIGINT, area DOUBLE, capital_city STRING, currency STRING) PARTITIONED BY (region STRING) STORED AS PARQUET LOCATION 's3://data-pipeline-country-population/curated/countries/'" \
  --query-execution-context Database=country_population \
  --result-configuration OutputLocation=s3://data-pipeline-country-population/athena-results/ \
  --region us-east-1

# 4. Run pipeline
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:$ACCOUNT_ID:stateMachine:country-population-etl-pipeline \
  --input '{}' \
  --region us-east-1

# 5. Check status
aws stepfunctions describe-execution \
  --execution-arn <EXECUTION_ARN> \
  --region us-east-1
```

Done! 🚀
