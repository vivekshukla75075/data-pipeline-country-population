# AWS Prerequisite Checklist for the Structured Ingestion Pipeline

This checklist is intended to prevent AWS-side access denied issues before deployment of the structured ingestion pipeline.

## 1. AWS account and region

- [ ] Confirm the target AWS account is correct.
- [ ] Confirm the deployment region is fixed, for example `us-east-1`.
- [ ] Ensure the AWS CLI is configured with the correct profile.
- [ ] Verify the active AWS identity has access to deploy resources.

## 2. Core S3 resources

- [ ] Create the data bucket for raw/validated/curated/logs storage.
- [ ] Create the Athena query results bucket.
- [ ] Verify S3 bucket names are known and consistent in the code and deployment templates.
- [ ] Ensure the bucket policies allow the required services and roles.
- [ ] Ensure the deployment identity can list and write to the bucket.

### Example bucket layout
- [ ] raw/
- [ ] validated/
- [ ] curated/
- [ ] logs/
- [ ] athena-results/

## 3. IAM roles and trust relationships

### Deployment role
- [ ] Create a deployment role for GitHub Actions or CI/CD.
- [ ] Configure the trust relationship so the deployment system can assume the role.
- [ ] Attach permissions for CloudFormation, S3, IAM, Glue, Lambda, Step Functions, and CloudWatch.
- [ ] Verify `iam:PassRole` is allowed where required.

### Glue job role
- [ ] Create a dedicated Glue job role.
- [ ] Attach S3 permissions for read/write/delete/list operations.
- [ ] Attach Glue catalog permissions if creating or updating tables.
- [ ] Attach CloudWatch Logs permissions.

### Lambda execution role
- [ ] Create a Lambda execution role.
- [ ] Attach S3 permissions if the Lambda writes or reads from S3.
- [ ] Attach CloudWatch Logs permissions.

### Step Functions execution role
- [ ] Create a Step Functions execution role.
- [ ] Allow it to start Glue jobs.
- [ ] Allow it to invoke Lambda if applicable.
- [ ] Allow it to write logs to CloudWatch.

## 4. Permissions for Glue

- [ ] The Glue role can read from the source S3 bucket.
- [ ] The Glue role can write to the validated and curated S3 prefixes.
- [ ] The Glue role can delete old objects during overwrite operations.
- [ ] The Glue role has permission to write logs.
- [ ] The Glue role can access Glue catalog metadata if needed.

### Minimum S3 actions
- [ ] `s3:GetObject`
- [ ] `s3:PutObject`
- [ ] `s3:DeleteObject`
- [ ] `s3:ListBucket`

## 5. Permissions for Lambda

- [ ] Lambda can write logs to CloudWatch.
- [ ] Lambda can read from the configured S3 bucket.
- [ ] Lambda can write raw data to the correct S3 prefix.
- [ ] Lambda can access any downstream service used in the workflow.

## 6. Permissions for Step Functions

- [ ] Step Functions can start Glue jobs.
- [ ] Step Functions can invoke Lambda if used.
- [ ] Step Functions can write execution logs.
- [ ] The state machine role is attached correctly.

## 7. CloudWatch Logs

- [ ] CloudWatch log groups exist or can be created.
- [ ] Execution roles can create log streams.
- [ ] Execution roles can put log events.
- [ ] Log retention is configured if needed.

## 8. Athena setup

- [ ] Create or confirm the Athena workgroup.
- [ ] Set the query result location to the Athena results bucket.
- [ ] Ensure the workgroup is enabled for query execution.
- [ ] Attach Athena, Glue, and S3 permissions to the identity used to query.
- [ ] Create or update the Glue catalog table for the curated layer.
- [ ] Ensure the table points to the curated Parquet location in S3.

## 9. Glue Data Catalog

- [ ] Confirm the database exists.
- [ ] Confirm the curated table exists.
- [ ] Confirm the partition structure matches the S3 layout.
- [ ] Confirm the table schema matches the curated Parquet files.

## 10. CloudFormation and deployment readiness

- [ ] The deployment principal can create CloudFormation stacks.
- [ ] The deployment principal can create IAM roles and policies.
- [ ] The deployment principal can upload deployment artifacts to S3.
- [ ] The deployment principal can create Glue jobs and Step Functions resources.
- [ ] The deployment principal can pass the required IAM roles to resources.

## 11. Pre-deployment verification steps

Before running the full automated deployment:
- [ ] Run a simple manual deployment test.
- [ ] Run a manual Glue job test.
- [ ] Run a manual S3 access test.
- [ ] Run a manual Athena query test.
- [ ] Verify logs in CloudWatch.

## 12. Common failure points to check first

If deployment or execution fails, check these first:
- [ ] missing IAM permissions
- [ ] missing `iam:PassRole`
- [ ] missing S3 delete permissions
- [ ] missing Glue catalog permissions
- [ ] missing Athena workgroup result location
- [ ] missing CloudWatch log permissions
- [ ] wrong AWS profile or region

## 13. Recommended order of execution

1. Create AWS roles and policies.
2. Create S3 buckets.
3. Configure Athena workgroup and result location.
4. Deploy CloudFormation or Terraform.
5. Run Glue jobs manually.
6. Validate Athena queries.
7. Enable CI/CD automation.

## 14. Final readiness sign-off

The project is ready for full automation only when all of the following are true:
- [ ] deployment succeeds without manual IAM fixes
- [ ] Glue jobs run successfully
- [ ] data lands in curated S3
- [ ] Athena can query the curated data
- [ ] logs are visible in CloudWatch
