"""
Image processing module for handling image captioning workflows.
Contains logic for processing images and detecting errors in responses.
"""

import os
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from .config import ERROR_MESSAGES
from .gemini_client import GeminiClient


class ImageProcessor:
    """Handles image processing operations."""

    def __init__(self, gemini_client=None):
        """Initialize with a Gemini client."""
        self.gemini_client = gemini_client or GeminiClient()
        self.shutdown_requested = False

    def set_shutdown_flag(self, flag):
        """Set shutdown flag for graceful termination."""
        self.shutdown_requested = flag

    def has_error_content(self, content):
        """Check if the content contains any error indicators."""
        content_lower = content.lower()
        return any(error_msg.lower() in content_lower for error_msg in ERROR_MESSAGES)

    def process_image(self, image_path, max_retries=5):
        """Process image using Gemini with key rotation."""
        return self.gemini_client.process_image_with_gemini(image_path, max_retries)

    def process_and_save(self, input_path, output_path, processed_files, checkpoint_file, pbar, max_retries=5):
        """Process a single image and save the result."""
        if self.shutdown_requested:
            pbar.update(1)
            return

        try:
            result = self.process_image(input_path, max_retries)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result)

            # Check if final result has errors before marking as processed
            has_errors = self.has_error_content(result)
            
            # Only mark as processed if there are no errors
            if not has_errors and processed_files is not None:
                from .config import INPUT_DIR
                relative_path = os.path.relpath(input_path, INPUT_DIR)
                with threading.Lock():
                    processed_files.add(relative_path)
                    if checkpoint_file:
                        import pickle
                        with open(checkpoint_file, 'wb') as f:
                            pickle.dump(processed_files, f)

            # Log status
            status = "❌ (still has errors)" if has_errors else "✅"
            from .config import INPUT_DIR
            relative_path = os.path.relpath(input_path, INPUT_DIR)
            logging.info(f"Processed: {relative_path} [Key #{self.gemini_client.current_key_index + 1}] {status}")

        except Exception as e:
            logging.error(f"Error in process_and_save for {input_path}: {str(e)}")
        finally:
            pbar.update(1)

    def process_images_batch(self, image_tasks, max_workers=10, max_retries=5):
        """Process a batch of images with threading."""
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []

            for task in image_tasks:
                if self.shutdown_requested:
                    break

                future = executor.submit(
                    self.process_and_save,
                    task['input_path'],
                    task['output_path'],
                    task.get('processed_files'),
                    task.get('checkpoint_file'),
                    task['pbar'],
                    max_retries
                )
                futures.append(future)

            # Wait for completion or shutdown
            for future in as_completed(futures):
                if self.shutdown_requested:
                    logging.info("⏹️  Cancelling remaining tasks...")
                    break
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"Error in future: {str(e)}")

    def get_stats(self):
        """Get processing statistics from the Gemini client."""
        return self.gemini_client.key_stats

    def log_stats(self):
        """Log current processing statistics."""
        self.gemini_client.log_key_stats()
