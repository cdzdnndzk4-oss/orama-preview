"""Private object storage. Local disk is available only for tests/pilot."""
import os
from pathlib import Path


class Storage:
    def __init__(self, bucket=None, local=None):
        self.bucket, self.local = bucket, Path(local) if local else None
        if bucket:
            import boto3
            self.client = boto3.client("s3")
        elif not self.local:
            raise RuntimeError("Private S3 bucket required")

    @classmethod
    def from_environment(cls, testing=False):
        bucket = os.getenv("ORAMA_S3_BUCKET")
        if bucket:
            return cls(bucket=bucket)
        if testing:
            return cls(local=os.getenv("ORAMA_TEST_STORAGE", "/tmp/orama-test-photos"))
        raise RuntimeError("ORAMA_S3_BUCKET required")

    def put(self, key, content, content_type):
        if self.bucket:
            self.client.put_object(Bucket=self.bucket, Key=key, Body=content, ContentType=content_type,
                                   ServerSideEncryption="AES256")
        else:
            destination = self.local / key
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)

    def get(self, key):
        if self.bucket:
            return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        return (self.local / key).read_bytes()
