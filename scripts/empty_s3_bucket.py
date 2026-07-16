#!/usr/bin/env python3
import sys
import logging
import boto3
from botocore.exceptions import ClientError

LOG = logging.getLogger('empty_s3_bucket')
LOG.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
LOG.addHandler(handler)


def delete_objects_batch(s3, bucket, objects):
    if not objects:
        return
    LOG.info('Deleting batch of %d objects from %s', len(objects), bucket)
    response = s3.delete_objects(Bucket=bucket, Delete={'Objects': objects})
    errors = response.get('Errors', [])
    if errors:
        for err in errors:
            LOG.error('Delete error: %s %s %s', err.get('Key'), err.get('VersionId'), err.get('Message'))
        raise RuntimeError('Failed to delete one or more objects from bucket: %s' % bucket)


def empty_bucket(bucket):
    s3 = boto3.client('s3')
    LOG.info('Emptying bucket: %s', bucket)
    deleted = 0

    try:
        paginator = s3.get_paginator('list_object_versions')
        page_iterator = paginator.paginate(Bucket=bucket)
        batch = []
        for page in page_iterator:
            for version in page.get('Versions', []):
                batch.append({'Key': version['Key'], 'VersionId': version['VersionId']})
                if len(batch) >= 1000:
                    delete_objects_batch(s3, bucket, batch)
                    deleted += len(batch)
                    batch = []
            for marker in page.get('DeleteMarkers', []):
                batch.append({'Key': marker['Key'], 'VersionId': marker['VersionId']})
                if len(batch) >= 1000:
                    delete_objects_batch(s3, bucket, batch)
                    deleted += len(batch)
                    batch = []
        if batch:
            delete_objects_batch(s3, bucket, batch)
            deleted += len(batch)

    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            LOG.warning('Bucket %s does not exist', bucket)
            return
        LOG.warning('list_object_versions failed for %s: %s', bucket, e)
    except Exception as e:
        LOG.error('Failed to delete object versions for %s: %s', bucket, e)
        raise

    # For non-versioned buckets, or if list_object_versions did not return any results,
    # also remove current objects.
    try:
        page_iterator = s3.get_paginator('list_objects_v2').paginate(Bucket=bucket)
        batch = []
        for page in page_iterator:
            for obj in page.get('Contents', []):
                batch.append({'Key': obj['Key']})
                if len(batch) >= 1000:
                    delete_objects_batch(s3, bucket, batch)
                    deleted += len(batch)
                    batch = []
        if batch:
            delete_objects_batch(s3, bucket, batch)
            deleted += len(batch)
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            LOG.warning('Bucket %s does not exist', bucket)
            return
        LOG.error('Failed to delete objects from %s: %s', bucket, e)
        raise

    LOG.info('Bucket %s emptied (%d delete operations)', bucket, deleted)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: empty_s3_bucket.py <bucket-name> [bucket-name ...]')
        sys.exit(1)

    for bucket_name in sys.argv[1:]:
        empty_bucket(bucket_name)
