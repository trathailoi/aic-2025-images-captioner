"""
File management module for handling file operations, checkpoints, and directory scanning.
"""

import os
import pickle
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from .config import INPUT_DIR, OUTPUT_DIR, IMAGE_EXTENSIONS, ERROR_MESSAGES


class FileManager:
    """Handles file operations and directory management."""

    def __init__(self, input_dir=None, output_dir=None):
        """Initialize with input and output directories."""
        self.input_dir = input_dir or INPUT_DIR
        self.output_dir = output_dir or OUTPUT_DIR

    def load_checkpoint(self, checkpoint_file='checkpoint.pkl'):
        """Load processed files from checkpoint."""
        if os.path.exists(checkpoint_file):
            with open(checkpoint_file, 'rb') as f:
                processed_files = pickle.load(f)
            logging.info(f"📂 Loaded checkpoint with {len(processed_files)} processed files.")
            return processed_files
        return set()

    def save_checkpoint(self, processed_files, checkpoint_file='checkpoint.pkl'):
        """Save processed files to checkpoint."""
        with open(checkpoint_file, 'wb') as f:
            pickle.dump(processed_files, f)

    def remove_checkpoint(self, checkpoint_file='checkpoint.pkl'):
        """Remove checkpoint file after completion."""
        if os.path.exists(checkpoint_file):
            os.remove(checkpoint_file)
            logging.info("🗑️  Processing completed. Checkpoint file removed.")

    def has_error_content(self, content):
        """Check if the content contains any error indicators."""
        content_lower = content.lower()
        return any(error_msg.lower() in content_lower for error_msg in ERROR_MESSAGES)

    def scan_for_error_files(self):
        """Scan all output files for errors and return list of files that need reprocessing."""
        error_files = []

        if not os.path.exists(self.output_dir):
            return error_files

        logging.info("🔍 Scanning existing output files for errors...")

        for root, _, files in os.walk(self.output_dir):
            for file in files:
                if file.endswith('.txt'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if self.has_error_content(content):
                                error_files.append(file_path)
                    except Exception as e:
                        logging.warning(f"Could not read file {file_path}: {e}")
                        error_files.append(file_path)  # Treat unreadable files as errors

        if error_files:
            logging.info(f"📊 Found {len(error_files)} files with errors that need reprocessing")
        else:
            logging.info("✅ No error files found")

        return error_files

    def mark_error_files_for_retry(self, processed_files, checkpoint_file='checkpoint.pkl'):
        """Mark error files for retry by removing them from processed_files."""
        error_files = self.scan_for_error_files()
        if error_files:
            for error_file in error_files:
                relative_path = os.path.relpath(error_file, self.output_dir)
                # Convert .txt back to original image extension
                base_name = os.path.splitext(relative_path)[0]

                # Try to find the corresponding image file
                for ext in IMAGE_EXTENSIONS:
                    potential_image = base_name + ext
                    if potential_image in processed_files:
                        processed_files.remove(potential_image)
                        logging.info(f"🔄 Marked for retry: {potential_image}")
                        break

            # Save updated checkpoint
            self.save_checkpoint(processed_files, checkpoint_file)
            logging.info(f"📝 Updated checkpoint: removed {len(error_files)} error files from processed list")

    def get_image_files(self):
        """Get all image files from input directory."""
        image_files = []
        for root, dirs, files in os.walk(self.input_dir):
            for file in files:
                if file.lower().endswith(IMAGE_EXTENSIONS):
                    image_files.append(os.path.join(root, file))
        return image_files

    def count_total_files(self):
        """Count total image files in input directory."""
        total_files = sum([len([f for f in files if f.lower().endswith(IMAGE_EXTENSIONS)])
                          for r, d, files in os.walk(self.input_dir)])
        return total_files

    def get_pending_files(self, processed_files):
        """Get list of files that haven't been processed yet."""
        pending_files = []

        for root, dirs, files in os.walk(self.input_dir):
            for file in files:
                if file.lower().endswith(IMAGE_EXTENSIONS):
                    input_path = os.path.join(root, file)
                    relative_path = os.path.relpath(input_path, self.input_dir)

                    if relative_path not in processed_files:
                        output_path = os.path.join(self.output_dir, os.path.splitext(relative_path)[0] + '.txt')
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)

                        pending_files.append({
                            'input_path': input_path,
                            'output_path': output_path,
                            'relative_path': relative_path
                        })

        return pending_files

    def get_error_file_inputs(self):
        """Get input files corresponding to error output files."""
        error_files = self.scan_for_error_files()
        input_files = []

        for error_file in error_files:
            relative_path = os.path.relpath(error_file, self.output_dir)

            # Try different image extensions
            for ext in IMAGE_EXTENSIONS:
                potential_input = os.path.join(self.input_dir, os.path.splitext(relative_path)[0] + ext)
                if os.path.exists(potential_input):
                    input_files.append({
                        'input_path': potential_input,
                        'output_path': error_file,
                        'relative_path': os.path.relpath(potential_input, self.input_dir)
                    })
                    break
            else:
                logging.warning(f"⚠️  Input file not found for: {relative_path}")

        return input_files

    def prepare_image_tasks(self, file_list, processed_files=None, checkpoint_file=None, pbar=None):
        """Prepare image processing tasks from file list."""
        tasks = []
        for file_info in file_list:
            task = {
                'input_path': file_info['input_path'],
                'output_path': file_info['output_path'],
                'processed_files': processed_files,
                'checkpoint_file': checkpoint_file,
                'pbar': pbar
            }
            tasks.append(task)
        return tasks
