"""S3 helper module for uploading files to AWS S3.

Description:
- Provides `upload_to_s3` to upload a local file to S3.
- Supports configuration via environment variables or `config/config.yml`.
- Honors `SKIP_S3_UPLOAD` (env) or `skip_s3_upload` in config to avoid uploads
- Can optionally assume an IAM role via STS when `ASSUME_ROLE_ARN` is provided.
"""

import boto3
import logging
import os
import json
from typing import Optional

logger = logging.getLogger(__name__)


def _load_config():
    # Environment variables take precedence over config file
    cfg = {}
    cfg['bucket'] = os.environ.get('S3_BUCKET')
    cfg['region'] = os.environ.get('AWS_REGION')
    cfg['skip_upload'] = os.environ.get('SKIP_S3_UPLOAD')
    cfg['assume_role_arn'] = os.environ.get('ASSUME_ROLE_ARN')

    # If any values missing, try loading config/config.yml (fallback to JSON if present)
    config_path_yml = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.yml')
    config_path_json = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.json')
    if (not cfg['bucket'] or not cfg['region'] or not cfg['skip_upload'] or not cfg['assume_role_arn']) and os.path.exists(config_path_yml):
        try:
            import yaml
            with open(config_path_yml, 'r', encoding='utf-8') as f:
                y = yaml.safe_load(f)
                cfg.setdefault('bucket', y.get('s3_bucket'))
                cfg.setdefault('region', y.get('aws_region'))
                cfg.setdefault('skip_upload', str(y.get('skip_s3_upload')))
                cfg.setdefault('assume_role_arn', y.get('assume_role_arn'))
        except Exception:
            logger.debug("yaml not available or failed to load %s", config_path_yml)
    elif (not cfg['bucket'] or not cfg['region']) and os.path.exists(config_path_json):
        try:
            with open(config_path_json, 'r', encoding='utf-8') as f:
                j = json.load(f)
                cfg.setdefault('bucket', j.get('s3_bucket'))
                cfg.setdefault('region', j.get('aws_region'))
                cfg.setdefault('skip_upload', str(j.get('skip_s3_upload')))
                cfg.setdefault('assume_role_arn', j.get('assume_role_arn'))
        except Exception:
            logger.debug("failed to load json config %s", config_path_json)

    # Normalize skip_upload to boolean
    skip = cfg.get('skip_upload')
    if isinstance(skip, str):
        cfg['skip_upload'] = skip.lower() in ('1', 'true', 'yes')
    else:
        cfg['skip_upload'] = bool(skip)

    return cfg


def _get_s3_client(region: Optional[str] = None, assume_role_arn: Optional[str] = None):
    # Create an S3 client; optionally assume role via STS
    if assume_role_arn:
        try:
            sts = boto3.client('sts')
            resp = sts.assume_role(RoleArn=assume_role_arn, RoleSessionName='pipeline-session')
            creds = resp['Credentials']
            session = boto3.Session(
                aws_access_key_id=creds['AccessKeyId'],
                aws_secret_access_key=creds['SecretAccessKey'],
                aws_session_token=creds['SessionToken'],
                region_name=region
            )
            return session.client('s3')
        except Exception:
            logger.exception("Failed to assume role %s", assume_role_arn)
            raise
    else:
        return boto3.client('s3', region_name=region)


def upload_to_s3(file_path: str, s3_key: str, bucket: Optional[str] = None) -> bool:
    """Upload a file to S3.

    Respects `SKIP_S3_UPLOAD` / `skip_s3_upload` and can assume a role via `ASSUME_ROLE_ARN`.
    """
    cfg = _load_config()
    if bucket is None:
        bucket = cfg.get('bucket') or 'my-bucket'

    if cfg.get('skip_upload'):
        logger.info("SKIP_S3_UPLOAD set — skipping upload of %s to s3://%s/%s", file_path, bucket, s3_key)
        return False

    region = cfg.get('region')
    assume_role = cfg.get('assume_role_arn')

    try:
        s3_client = _get_s3_client(region=region, assume_role_arn=assume_role)
        s3_client.upload_file(file_path, bucket, s3_key)
        logger.info("Successfully uploaded %s to s3://%s/%s", file_path, bucket, s3_key)
        return True
    except Exception:
        logger.exception("Error uploading %s to s3://%s/%s", file_path, bucket, s3_key)
        logger.info("Note: S3 upload skipped or failed (check AWS credentials / permissions)")
        return False
