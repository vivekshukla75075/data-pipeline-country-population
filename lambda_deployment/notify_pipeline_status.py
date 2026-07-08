"""Lambda function to send deployment/status notifications to SQS and SNS."""

import json
import os
import boto3

sqs_client = boto3.client("sqs")
sns_client = boto3.client("sns")


def lambda_handler(event, context):
    """Send a pipeline status message to SQS and SNS."""
    payload = event.get("Payload", event) if isinstance(event, dict) else event
    status = payload.get("status", "UNKNOWN")
    stage = payload.get("stage", "pipeline")
    message = payload.get("message", f"{stage} status: {status}")
    reason = payload.get("reason") or payload.get("error") or payload.get("failureReason")

    details = {
        "status": status,
        "stage": stage,
        "message": message,
        "reason": reason,
        "source": payload.get("source", "stepfunctions"),
        "executionArn": payload.get("executionArn"),
        "timestamp": payload.get("timestamp"),
    }

    queue_url = os.environ.get("NOTIFICATION_QUEUE_URL")
    topic_arn = os.environ.get("NOTIFICATION_TOPIC_ARN")

    if queue_url:
        sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(details, default=str),
        )

    if topic_arn:
        sns_client.publish(
            TopicArn=topic_arn,
            Subject=f"Data Pipeline {status}",
            Message=json.dumps(details, default=str),
        )

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "notification sent", **details}),
    }
