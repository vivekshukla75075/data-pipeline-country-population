resource "aws_sfn_state_machine" "etl_pipeline" {
  name       = "country-population-etl-pipeline"
  role_arn   = aws_iam_role.step_functions_role.arn
  definition = <<JSON
{
  "Comment": "ETL Pipeline Orchestration",
  "StartAt": "IngestData",
  "States": {
    "IngestData": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.trigger_ingestion.arn}",
      "Next": "ValidateData",
      "Catch": [{
        "ErrorEquals": ["States.ALL"],
        "Next": "ErrorHandler"
      }]
    },
    "ValidateData": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.trigger_validation.arn}",
      "Next": "TransformData",
      "Catch": [{
        "ErrorEquals": ["States.ALL"],
        "Next": "ErrorHandler"
      }]
    },
    "TransformData": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.trigger_transformation.arn}",
      "Next": "UpdateDataCatalog",
      "Catch": [{
        "ErrorEquals": ["States.ALL"],
        "Next": "ErrorHandler"
      }]
    },
    "UpdateDataCatalog": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.create_glue_catalog.arn}",
      "Next": "QueryAthena",
      "Catch": [{
        "ErrorEquals": ["States.ALL"],
        "Next": "ErrorHandler"
      }]
    },
    "QueryAthena": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.query_athena.arn}",
      "Next": "Success",
      "Catch": [{
        "ErrorEquals": ["States.ALL"],
        "Next": "ErrorHandler"
      }]
    },
    "Success": {
      "Type": "Succeed"
    },
    "ErrorHandler": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:error-handler",
      "Next": "Failure"
    },
    "Failure": {
      "Type": "Fail"
    }
  }
}
JSON
}
