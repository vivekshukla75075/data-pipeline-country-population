"""Lambda that starts the validation Glue job from an SQS trigger."""

import json
import os
import boto3


def _get_glue_client():
    """Create a Glue client using the configured AWS region when available."""
    region_name = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
    return boto3.client("glue", region_name=region_name)


def get_job_name(message_body, default_job_name):
    """Extract the Glue job name from a queue message payload."""
    if not isinstance(message_body, dict):
        return default_job_name

    return (
        message_body.get("jobName")
        or message_body.get("JobName")
        or message_body.get("job_name")
        or default_job_name
    )


def lambda_handler(event, context):
    """Start a Glue validation job for each received SQS event record."""
    default_job_name = os.environ.get("GLUE_JOB_NAME", "country-population-validation")
    results = []

    glue_client = _get_glue_client()

    for record in event.get("Records", []):
        body = record.get("body", "{}")

        try:
            message_body = json.loads(body) if isinstance(body, str) else body
        except json.JSONDecodeError:
            message_body = {"raw_body": body}

        job_name = get_job_name(message_body, default_job_name)
        response = glue_client.start_job_run(JobName=job_name)
        results.append({"jobName": job_name, "runId": response.get("JobRunId")})

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "validation jobs started", "results": results}),
    }
