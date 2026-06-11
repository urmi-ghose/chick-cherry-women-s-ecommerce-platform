from django.core.files.storage import Storage
from django.core.files.base import File
from minio import Minio
from minio.error import S3Error
from django.conf import settings
import os
from urllib.parse import urljoin


class MinIOMediaStorage(Storage):
    """
    Custom Django storage backend for MinIO S3-compatible storage.
    """

    def __init__(self):
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_HTTPS,
        )
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self.location = "media"
        self.file_overwrite = False

        # Ensure bucket exists
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except S3Error as e:
            raise Exception(f"MinIO bucket error: {e}")

    def _get_key_name(self, name):
        """Generate the key name for the file in MinIO."""
        return os.path.join(self.location, name)

    def _open(self, name, mode="rb"):
        """Retrieve the file from MinIO."""
        try:
            response = self.client.get_object(
                self.bucket_name, self._get_key_name(name)
            )
            return File(response, name)
        except S3Error as e:
            raise FileNotFoundError(f"File {name} not found in MinIO: {e}")

    def _save(self, name, content):
        """Save the file to MinIO."""
        if not self.file_overwrite and self.exists(name):
            # Generate a new name if file exists and overwrite is disabled
            name = self.get_available_name(name)

        key_name = self._get_key_name(name)

        try:
            # Get content size
            content.seek(0, os.SEEK_END)
            size = content.tell()
            content.seek(0)

            # Upload to MinIO
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=key_name,
                data=content,
                length=size,
                content_type=getattr(
                    content, "content_type", "application/octet-stream"
                ),
            )
            return name
        except S3Error as e:
            raise Exception(f"Failed to save file to MinIO: {e}")

    def delete(self, name):
        """Delete the file from MinIO."""
        try:
            self.client.remove_object(self.bucket_name, self._get_key_name(name))
        except S3Error:
            # File doesn't exist, ignore
            pass

    def exists(self, name):
        """Check if the file exists in MinIO."""
        try:
            self.client.stat_object(self.bucket_name, self._get_key_name(name))
            return True
        except S3Error:
            return False

    def listdir(self, path):
        """List files and directories in the given path."""
        try:
            objects = self.client.list_objects(
                self.bucket_name, prefix=os.path.join(self.location, path)
            )
            files = []
            dirs = set()

            for obj in objects:
                # Remove the location prefix
                rel_path = obj.object_name[len(self.location) + 1 :]
                if "/" in rel_path:
                    dirs.add(rel_path.split("/")[0])
                else:
                    files.append(rel_path)

            return list(dirs), files
        except S3Error:
            return [], []

    def size(self, name):
        """Get the size of the file."""
        try:
            stat = self.client.stat_object(self.bucket_name, self._get_key_name(name))
            return stat.size
        except S3Error as e:
            raise FileNotFoundError(f"File {name} not found: {e}")

    def url(self, name):
        """Generate the URL for the file."""
        protocol = "https" if settings.MINIO_USE_HTTPS else "http"
        base_url = f"{protocol}://{settings.MINIO_ENDPOINT}"
        return urljoin(base_url, f"{self.bucket_name}/{self._get_key_name(name)}")

    def accessed_time(self, name):
        """Get the last accessed time (not supported by MinIO, return modified time)."""
        return self.modified_time(name)

    def created_time(self, name):
        """Get the creation time (not supported by MinIO, return modified time)."""
        return self.modified_time(name)

    def modified_time(self, name):
        """Get the last modified time."""
        try:
            stat = self.client.stat_object(self.bucket_name, self._get_key_name(name))
            return stat.last_modified
        except S3Error as e:
            raise FileNotFoundError(f"File {name} not found: {e}")


class MediaStorage(MinIOMediaStorage):
    """Alias for backward compatibility."""

    pass
