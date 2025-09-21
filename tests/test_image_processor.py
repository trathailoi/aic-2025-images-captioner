"""
Unit tests for image_processor module.
"""

import unittest
import os
import tempfile
import threading
from unittest.mock import Mock, patch, MagicMock
from tqdm import tqdm

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.image_processor import ImageProcessor
from src.gemini_client import GeminiClient


class TestImageProcessor(unittest.TestCase):
    """Test ImageProcessor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_gemini_client = Mock(spec=GeminiClient)
        self.processor = ImageProcessor(self.mock_gemini_client)

    def test_init_default_client(self):
        """Test initialization with default client."""
        with patch('image_processor.GeminiClient') as mock_client_class:
            processor = ImageProcessor()
            mock_client_class.assert_called_once()

    def test_init_custom_client(self):
        """Test initialization with custom client."""
        processor = ImageProcessor(self.mock_gemini_client)
        self.assertEqual(processor.gemini_client, self.mock_gemini_client)
        self.assertFalse(processor.shutdown_requested)

    def test_set_shutdown_flag(self):
        """Test setting shutdown flag."""
        self.assertFalse(self.processor.shutdown_requested)
        self.processor.set_shutdown_flag(True)
        self.assertTrue(self.processor.shutdown_requested)

    def test_has_error_content(self):
        """Test error content detection."""
        # Test content with errors
        self.assertTrue(self.processor.has_error_content("An internal error has occurred"))
        self.assertTrue(self.processor.has_error_content("500 Internal Server Error"))
        self.assertTrue(self.processor.has_error_content("Error processing"))
        self.assertTrue(self.processor.has_error_content("Max retries exceeded"))

        # Test content without errors
        self.assertFalse(self.processor.has_error_content("Normal response content"))
        self.assertFalse(self.processor.has_error_content("Processing completed successfully"))

    def test_process_image(self):
        """Test image processing delegation."""
        self.mock_gemini_client.process_image_with_gemini.return_value = "Test result"

        result = self.processor.process_image("test_image.jpg", max_retries=5)

        self.assertEqual(result, "Test result")
        self.mock_gemini_client.process_image_with_gemini.assert_called_once_with("test_image.jpg", 5)

    @patch('builtins.open', create=True)
    @patch('os.path.relpath')
    @patch('pickle.dump')
    @patch('threading.Lock')
    def test_process_and_save_success(self, mock_lock, mock_pickle_dump, mock_relpath, mock_open):
        """Test successful process and save operation."""
        # Setup mocks
        mock_relpath.return_value = "test_image.jpg"
        self.mock_gemini_client.process_image_with_gemini.return_value = "Success result"
        self.mock_gemini_client.current_key_index = 0

        # Mock file operations
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock progress bar
        mock_pbar = Mock()

        # Mock processed files and checkpoint
        processed_files = set()

        # Test
        self.processor.process_and_save(
            "input/test_image.jpg",
            "output/test_image.txt",
            processed_files,
            "checkpoint.pkl",
            mock_pbar,
            max_retries=5
        )

        # Verify file was written
        mock_file.write.assert_called_once_with("Success result")

        # Verify progress bar was updated
        mock_pbar.update.assert_called_once_with(1)

        # Verify processed files was updated
        self.assertIn("test_image.jpg", processed_files)

    @patch('builtins.open', create=True)
    @patch('os.path.relpath')
    def test_process_and_save_with_shutdown(self, mock_relpath, mock_open):
        """Test process and save with shutdown flag set."""
        # Set shutdown flag
        self.processor.set_shutdown_flag(True)

        # Mock progress bar
        mock_pbar = Mock()

        # Test
        self.processor.process_and_save(
            "input/test_image.jpg",
            "output/test_image.txt",
            None,
            None,
            mock_pbar
        )

        # Should only update progress bar, not process image
        mock_pbar.update.assert_called_once_with(1)
        self.mock_gemini_client.process_image_with_gemini.assert_not_called()
        mock_open.assert_not_called()

    @patch('builtins.open', create=True)
    @patch('os.path.relpath')
    def test_process_and_save_exception(self, mock_relpath, mock_open):
        """Test process and save with exception."""
        # Setup mocks
        mock_relpath.return_value = "test_image.jpg"
        self.mock_gemini_client.process_image_with_gemini.side_effect = Exception("Test error")

        # Mock progress bar
        mock_pbar = Mock()

        # Test
        with patch('logging.error') as mock_log_error:
            self.processor.process_and_save(
                "input/test_image.jpg",
                "output/test_image.txt",
                None,
                None,
                mock_pbar
            )

        # Should log error and update progress bar
        mock_log_error.assert_called_once()
        mock_pbar.update.assert_called_once_with(1)

    @patch('image_processor.ThreadPoolExecutor')
    @patch('image_processor.as_completed')
    def test_process_images_batch(self, mock_as_completed, mock_thread_pool):
        """Test batch image processing."""
        # Setup mocks
        mock_executor = Mock()
        mock_thread_pool.return_value.__enter__.return_value = mock_executor

        mock_future1 = Mock()
        mock_future2 = Mock()
        mock_executor.submit.side_effect = [mock_future1, mock_future2]
        mock_as_completed.return_value = [mock_future1, mock_future2]

        # Test tasks
        tasks = [
            {
                'input_path': 'input1.jpg',
                'output_path': 'output1.txt',
                'processed_files': set(),
                'checkpoint_file': 'checkpoint.pkl',
                'pbar': Mock()
            },
            {
                'input_path': 'input2.jpg',
                'output_path': 'output2.txt',
                'processed_files': set(),
                'checkpoint_file': 'checkpoint.pkl',
                'pbar': Mock()
            }
        ]

        # Test
        self.processor.process_images_batch(tasks, max_workers=2, max_retries=3)

        # Verify thread pool was configured correctly
        mock_thread_pool.assert_called_once_with(max_workers=2)

        # Verify tasks were submitted
        self.assertEqual(mock_executor.submit.call_count, 2)

    def test_get_stats(self):
        """Test getting statistics."""
        mock_stats = {'key1': {'requests': 10, 'errors': 1}}
        self.mock_gemini_client.key_stats = mock_stats

        stats = self.processor.get_stats()
        self.assertEqual(stats, mock_stats)

    def test_log_stats(self):
        """Test logging statistics."""
        self.processor.log_stats()
        self.mock_gemini_client.log_key_stats.assert_called_once()


if __name__ == '__main__':
    unittest.main()
