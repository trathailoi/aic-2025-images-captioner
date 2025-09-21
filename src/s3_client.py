"""
S3 client module for handling AWS S3 operations.
Manages file listing, downloading, and uploading for the image captioning system.
"""

import os
import logging
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import List, Tuple, Optional
from dotenv import load_dotenv

from .config import IMAGE_EXTENSIONS

load_dotenv()

class S3Client:
    """Handles S3 operations for image processing."""

    def __init__(self, region: str = "ap-southeast-1", bucket_name: str = "aic-2025-bucket"):
        """Initialize S3 client with credentials from environment."""
        self.region = region
        self.bucket_name = bucket_name
        self.images_folder = "frames"
        self.captions_folder = "captions"

        try:
            self.s3_client = boto3.client(
                's3',
                region_name=self.region,
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logging.info(f"Successfully connected to S3 bucket: {self.bucket_name}")
        except NoCredentialsError:
            logging.error("AWS credentials not found. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
            raise
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logging.error(f"S3 bucket '{self.bucket_name}' not found")
            else:
                logging.error(f"Error connecting to S3: {e}")
            raise

    def list_all_images(self) -> List[str]:
        """List all image files in the S3 frames folder."""
        image_files = []
        continuation_token = None

        logging.info(f"Scanning S3 bucket for images...")

        while True:
            try:
                list_params = {
                    'Bucket': self.bucket_name,
                    'Prefix': f"{self.images_folder}/",
                    'MaxKeys': 1000
                }

                if continuation_token:
                    list_params['ContinuationToken'] = continuation_token

                response = self.s3_client.list_objects_v2(**list_params)

                if 'Contents' in response:
                    for obj in response['Contents']:
                        key = obj['Key']
                        if key.endswith('/'):
                            continue

                        if any(key.lower().endswith(ext) for ext in IMAGE_EXTENSIONS):
                            image_files.append(key)

                if response.get('IsTruncated', False):
                    continuation_token = response.get('NextContinuationToken')
                else:
                    break

            except ClientError as e:
                logging.error(f"Error listing S3 objects: {e}")
                raise

        logging.info(f"Found {len(image_files)} image files in S3 bucket")
        return image_files

    def check_caption_exists(self, image_s3_key: str) -> bool:
        """Check if a caption file already exists for an image."""
        caption_key = self.get_caption_key_from_image_key(image_s3_key)

        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=caption_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                return False

    def get_caption_key_from_image_key(self, image_key: str) -> str:
        """Convert image S3 key to caption S3 key."""
        relative_path = image_key.replace(f"{self.images_folder}/", "", 1)
        base_name = os.path.splitext(relative_path)[0]
        return f"{self.captions_folder}/{base_name}.txt"

    def generate_work_distribution(self, image_files: List[str], num_workers: int = 1) -> List[List[str]]:
        """Distribute image files across multiple workers for parallel processing."""
        if num_workers <= 1:
            return [image_files]

        logging.info("Filtering out images that already have captions...")

        images_to_process = []
        for image_key in image_files:
            if not self.check_caption_exists(image_key):
                images_to_process.append(image_key)

        logging.info(f"Images needing processing: {len(images_to_process)} out of {len(image_files)} total")

        chunk_size = len(images_to_process) // num_workers
        remainder = len(images_to_process) % num_workers

        work_chunks = []
        start_idx = 0

        for i in range(num_workers):
            current_chunk_size = chunk_size + (1 if i < remainder else 0)

            if current_chunk_size > 0:
                end_idx = start_idx + current_chunk_size
                work_chunks.append(images_to_process[start_idx:end_idx])
                start_idx = end_idx

        return work_chunks

    def save_work_distribution_files(self, work_chunks: List[List[str]], output_dir: str = "./work_distribution") -> List[str]:
        """Save work distribution to files for teammates."""
        os.makedirs(output_dir, exist_ok=True)

        distribution_files = []

        for i, chunk in enumerate(work_chunks):
            if chunk:
                filename = f"worker_{i+1}_images.txt"
                filepath = os.path.join(output_dir, filename)

                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"# Work assignment for Worker {i+1}\n")
                    f.write(f"# Total images to process: {len(chunk)}\n")
                    f.write(f"# S3 Bucket: {self.bucket_name}\n")
                    f.write(f"# AWS Region: {self.region}\n\n")

                    for image_key in chunk:
                        f.write(f"{image_key}\n")

                distribution_files.append(filepath)
                logging.info(f"Created work file: {filename} ({len(chunk)} images)")

        summary_file = os.path.join(output_dir, "distribution_summary.txt")
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("# Work Distribution Summary\n")
            f.write(f"# Total workers: {len(work_chunks)}\n")
            f.write(f"# Total images: {sum(len(chunk) for chunk in work_chunks)}\n")
            f.write(f"# S3 Bucket: {self.bucket_name}\n")
            f.write(f"# AWS Region: {self.region}\n\n")

            for i, chunk in enumerate(work_chunks):
                if chunk:
                    f.write(f"Worker {i+1}: {len(chunk)} images (worker_{i+1}_images.txt)\n")

        distribution_files.append(summary_file)
        logging.info(f"Created summary file: distribution_summary.txt")

        return distribution_files
