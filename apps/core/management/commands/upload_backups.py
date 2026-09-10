from pathlib import Path
from hashlib import sha256
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Upload private PostgreSQL dumps to the configured backup bucket using the instance role."

    def add_arguments(self, parser):
        parser.add_argument("--source", default="/backups")

    def handle(self, *args, **options):
        import boto3
        from botocore.exceptions import ClientError
        bucket = getattr(settings, "AWS_BACKUP_BUCKET_NAME", "")
        if not bucket:
            raise CommandError("Set AWS_BACKUP_BUCKET_NAME before uploading backups.")
        files = list(Path(options["source"]).glob("nlk-*.dump"))
        if not files:
            raise CommandError("No backup dumps found.")
        client = boto3.client("s3", region_name=getattr(settings, "AWS_S3_REGION_NAME", None))
        for file in files:
            if file.stat().st_size < 100:
                raise CommandError("Backup is empty or incomplete.")
            key = "database/" + file.name
            with file.open("rb") as stream:
                digest = sha256()
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            checksum = digest.hexdigest()
            try:
                remote = client.head_object(Bucket=bucket, Key=key)
            except ClientError as exc:
                if exc.response["Error"]["Code"] not in {"404", "NoSuchKey", "NotFound"}:
                    raise
            else:
                if remote.get("Metadata", {}).get("sha256") == checksum:
                    continue
                raise CommandError("An existing backup key differs; refusing to overwrite it.")
            client.upload_file(str(file), bucket, key, ExtraArgs={
                "ServerSideEncryption": "AES256", "Metadata": {"sha256": checksum},
            })
            if client.head_object(Bucket=bucket, Key=key)["ContentLength"] != file.stat().st_size:
                raise CommandError("Backup upload verification failed.")
        self.stdout.write(f"Verified {len(files)} backup file(s) in private storage.")
