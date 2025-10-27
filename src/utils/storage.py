"""Storage utilities for MinIO/S3."""
import os
import io
from typing import Optional
from datetime import datetime
import logging
from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)


class MinIOStorage:
    """MinIO/S3 storage manager for news data."""

    def __init__(self):
        """Initialize MinIO client."""
        self.endpoint = os.getenv('MINIO_ENDPOINT', 'minio:9000')
        self.access_key = os.getenv('MINIO_ROOT_USER', 'minioadmin')
        self.secret_key = os.getenv('MINIO_ROOT_PASSWORD', 'minioadmin')
        self.bucket_name = os.getenv('MINIO_BUCKET_NAME', 'news-storage')
        self.secure = os.getenv('MINIO_SECURE', 'false').lower() == 'true'

        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )

        # Ensure bucket exists
        self._ensure_bucket()

    def _ensure_bucket(self):
        """Ensure the bucket exists, create if it doesn't."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
            else:
                logger.info(f"Bucket {self.bucket_name} already exists")
        except S3Error as e:
            logger.error(f"Error ensuring bucket exists: {e}")
            raise

    def upload_html(self, url: str, html_content: str, portal: str) -> Optional[str]:
        """
        Upload raw HTML to MinIO.

        Args:
            url: Article URL (used for generating key)
            html_content: HTML content
            portal: Portal name

        Returns:
            S3 key if successful, None otherwise
        """
        try:
            # Generate S3 key
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            url_hash = abs(hash(url)) % (10 ** 8)
            s3_key = f"html/{portal}/{timestamp}_{url_hash}.html"

            # Upload to MinIO
            html_bytes = html_content.encode('utf-8')
            self.client.put_object(
                self.bucket_name,
                s3_key,
                data=io.BytesIO(html_bytes),
                length=len(html_bytes),
                content_type='text/html'
            )

            logger.info(f"Uploaded HTML to {s3_key}")
            return s3_key

        except S3Error as e:
            logger.error(f"Error uploading HTML: {e}")
            return None

    def upload_summary(self, summary_text: str, summary_date: str) -> Optional[str]:
        """
        Upload summary text to MinIO.

        Args:
            summary_text: Summary text
            summary_date: Summary date (YYYY-MM-DD format)

        Returns:
            S3 key if successful, None otherwise
        """
        try:
            # Generate S3 key
            s3_key = f"summaries/{summary_date}.txt"

            # Upload to MinIO
            summary_bytes = summary_text.encode('utf-8')
            self.client.put_object(
                self.bucket_name,
                s3_key,
                data=io.BytesIO(summary_bytes),
                length=len(summary_bytes),
                content_type='text/plain'
            )

            logger.info(f"Uploaded summary to {s3_key}")
            return s3_key

        except S3Error as e:
            logger.error(f"Error uploading summary: {e}")
            return None

    def download_object(self, s3_key: str) -> Optional[str]:
        """
        Download object from MinIO.

        Args:
            s3_key: S3 key

        Returns:
            Object content as string if successful, None otherwise
        """
        try:
            response = self.client.get_object(self.bucket_name, s3_key)
            content = response.read().decode('utf-8')
            response.close()
            response.release_conn()

            logger.info(f"Downloaded {s3_key}")
            return content

        except S3Error as e:
            logger.error(f"Error downloading object: {e}")
            return None

    def delete_object(self, s3_key: str) -> bool:
        """
        Delete object from MinIO.

        Args:
            s3_key: S3 key

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.remove_object(self.bucket_name, s3_key)
            logger.info(f"Deleted {s3_key}")
            return True

        except S3Error as e:
            logger.error(f"Error deleting object: {e}")
            return False

    def list_objects(self, prefix: str = '') -> list:
        """
        List objects in MinIO with a given prefix.

        Args:
            prefix: Prefix to filter objects

        Returns:
            List of object names
        """
        try:
            objects = self.client.list_objects(
                self.bucket_name,
                prefix=prefix,
                recursive=True
            )
            return [obj.object_name for obj in objects]

        except S3Error as e:
            logger.error(f"Error listing objects: {e}")
            return []

    def get_presigned_url(self, s3_key: str, expires: int = 3600) -> Optional[str]:
        """
        Get presigned URL for an object.

        Args:
            s3_key: S3 key
            expires: URL expiration time in seconds

        Returns:
            Presigned URL if successful, None otherwise
        """
        try:
            from datetime import timedelta
            url = self.client.presigned_get_object(
                self.bucket_name,
                s3_key,
                expires=timedelta(seconds=expires)
            )
            return url

        except S3Error as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None


if __name__ == '__main__':
    # Test storage
    storage = MinIOStorage()
    print("MinIO storage initialized successfully")

    # Test upload
    test_html = "<html><body>Test</body></html>"
    key = storage.upload_html("http://test.com", test_html, "test-portal")
    print(f"Uploaded test HTML: {key}")

    # Test download
    if key:
        content = storage.download_object(key)
        print(f"Downloaded content: {content[:50]}...")
