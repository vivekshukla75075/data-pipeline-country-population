**Glue Test Job**

Purpose: Standalone Glue ETL to test reading CSV/Parquet from S3, simple Spark transforms, and writing results to S3 with logs available in CloudWatch.

Files added:

- [infra/cloudformation/glue-test-job-resources.yaml](infra/cloudformation/glue-test-job-resources.yaml): CloudFormation to create a test S3 bucket and an IAM role for Glue.
- [scripts/glue_test_job.py](scripts/glue_test_job.py): PySpark script to run on Glue.

Quick deploy & run

1. Deploy the CloudFormation stack (creates bucket + role). Replace `--region` and `Environment` as needed.

```bash
aws cloudformation deploy \
  --template-file infra/cloudformation/glue-test-job-resources.yaml \
  --stack-name data-pipeline-glue-test \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides Environment=dev \
  --region us-east-1
```

2. Get outputs (bucket and role ARN):

```bash
BUCKET=$(aws cloudformation describe-stacks --stack-name data-pipeline-glue-test --region us-east-1 --query 'Stacks[0].Outputs[?OutputKey==`GlueTestBucketName`].OutputValue' --output text)
ROLE_ARN=$(aws cloudformation describe-stacks --stack-name data-pipeline-glue-test --region us-east-1 --query 'Stacks[0].Outputs[?OutputKey==`GlueJobRoleArn`].OutputValue' --output text)
echo $BUCKET $ROLE_ARN
```

3. Upload the script and a small sample CSV to the bucket:

```bash
aws s3 cp scripts/glue_test_job.py s3://$BUCKET/glue-scripts/glue_test_job.py
# upload a sample CSV (create locally or use existing)
aws s3 cp sample_data/test.csv s3://$BUCKET/input/test.csv
```

4. Create a Glue job (example using Glue 3.0 Spark runtime):

```bash
aws glue create-job \
  --name glue-test-job \
  --role $ROLE_ARN \
  --command '{"Name":"glueetl","ScriptLocation":"s3://'$BUCKET'/glue-scripts/glue_test_job.py","PythonVersion":"3"}' \
  --glue-version "3.0" \
  --region us-east-1
```

5. Start the job run:

```bash
aws glue start-job-run --job-name glue-test-job --arguments='--JOB_NAME=glue-test-job,--INPUT_PATH=s3://'$BUCKET'/input/,--OUTPUT_PATH=s3://'$BUCKET'/output/,--INPUT_FORMAT=csv' --region us-east-1
```

6. Tail logs in CloudWatch (replace `--region`):

```bash
# find the log stream for the run in CloudWatch Logs under /aws-glue
aws logs describe-log-streams --log-group-name /aws-glue --region us-east-1 --order-by LastEventTime --descending --max-items 50
aws logs get-log-events --log-group-name /aws-glue --log-stream-name <log-stream-name> --region us-east-1
```

Notes:

- The CloudFormation template creates a bucket and an IAM role scoped to that bucket; this avoids global S3 permissions problems.
- If you want to use an existing bucket, pass `BucketName` when deploying the CloudFormation stack.
- The AWS identity that deploys the CloudFormation stack needs permissions to create IAM roles and S3 buckets.
