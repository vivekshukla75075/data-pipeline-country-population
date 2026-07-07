# Quick Start Guide

## 1. Complete Automated Deployment

```bash
# Run full deployment
chmod +x infrastructure/scripts/full_deployment.sh
./infrastructure/scripts/full_deployment.sh
```

This will:
- Create S3 bucket
- Upload scripts
- Create Glue jobs
- Create Lambda functions
- Create Step Functions state machine
- Create Athena tables

## 2. Upload Sample Data

```bash
# Create and upload sample data
cat > /tmp/countries.json <<'EOF'
[
  {
    "name": {"common": "United States"},
    "region": "Americas",
    "population": 331900000,
    "area": 9833517,
    "capital": ["Washington, D.C."],
    "currencies": {"USD": {"name": "US Dollar"}}
  }
]
EOF

aws s3 cp /tmp/countries.json s3://data-pipeline-country-population/raw/countries/countries_raw.json
```

## 3. Trigger Pipeline

```bash
# Get your account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Start execution
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:$ACCOUNT_ID:stateMachine:country-population-etl-pipeline \
  --input '{}' \
  --region us-east-1
```

## 4. Monitor Execution

```bash
# View in AWS Console
# https://console.aws.amazon.com/states/home?region=us-east-1#/statemachines
```

## 5. Query Results

```bash
# Run Athena query
SELECT region, SUM(population) FROM country_population.countries_curated GROUP BY region
```

## Troubleshooting

### Step Functions not showing up
```bash
aws stepfunctions create_step_functions.sh
```

### Lambda functions missing
```bash
# Redeploy
./infrastructure/scripts/deploy_pipeline.sh
```

### Check resources
```bash
# List state machines
aws stepfunctions list-state-machines --region us-east-1

# List Lambda functions
aws lambda list-functions --region us-east-1

# List Glue jobs
aws glue list-jobs --region us-east-1
```
