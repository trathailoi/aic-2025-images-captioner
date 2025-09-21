"""
Unit tests for file_manager module.
"""

import unittest
import os
import tempfile
import pickle
from unittest.mock import Mock, patch, mock_open, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.file_manager import FileManager


class TestFileManager(unittest.TestCase):
    """Test FileManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.input_dir = os.path.join(self.temp_dir, "input")
        self.output_dir = os.path.join(self.temp_dir, "output")
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

        self.file_manager = FileManager(self.input_dir, self.output_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_default_dirs(self):
        """Test initialization with default directories."""
        fm = FileManager()
        from config import INPUT_DIR, OUTPUT_DIR
        self.assertEqual(fm.input_dir, INPUT_DIR)
        self.assertEqual(fm.output_dir, OUTPUT_DIR)

    def test_init_custom_dirs(self):
        """Test initialization with custom directories."""
        self.assertEqual(self.file_manager.input_dir, self.input_dir)
        self.assertEqual(self.file_manager.output_dir, self.output_dir)

    @patch('os.path.exists')
    @patch('pickle.load')
    @patch('builtins.open', create=True)
    def test_load_checkpoint_exists(self, mock_open_func, mock_pickle_load, mock_exists):
        """Test loading existing checkpoint."""
        # Setup mocks
        mock_exists.return_value = True
        test_processed_files = {'file1.jpg', 'file2.jpg'}
        mock_pickle_load.return_value = test_processed_files

        # Test
        with patch('logging.info') as mock_log:
            result = self.file_manager.load_checkpoint('test_checkpoint.pkl')

        # Verify
        self.assertEqual(result, test_processed_files)
        mock_open_func.assert_called_once_with('test_checkpoint.pkl', 'rb')
        mock_pickle_load.assert_called_once()
        mock_log.assert_called_once()

    @patch('os.path.exists')
    def test_load_checkpoint_not_exists(self, mock_exists):
        """Test loading non-existent checkpoint."""
        mock_exists.return_value = False

        result = self.file_manager.load_checkpoint('test_checkpoint.pkl')

        self.assertEqual(result, set())

    @patch('pickle.dump')
    @patch('builtins.open', create=True)
    def test_save_checkpoint(self, mock_open_func, mock_pickle_dump):
        """Test saving checkpoint."""
        test_processed_files = {'file1.jpg', 'file2.jpg'}

        self.file_manager.save_checkpoint(test_processed_files, 'test_checkpoint.pkl')

        mock_open_func.assert_called_once_with('test_checkpoint.pkl', 'wb')
        mock_pickle_dump.assert_called_once_with(test_processed_files, mock_open_func.return_value.__enter__.return_value)

    @patch('os.path.exists')
    @patch('os.remove')
    def test_remove_checkpoint_exists(self, mock_remove, mock_exists):
        """Test removing existing checkpoint."""
        mock_exists.return_value = True

        with patch('logging.info') as mock_log:
            self.file_manager.remove_checkpoint('test_checkpoint.pkl')

        mock_remove.assert_called_once_with('test_checkpoint.pkl')
        mock_log.assert_called_once()

    @patch('os.path.exists')
    @patch('os.remove')
    def test_remove_checkpoint_not_exists(self, mock_remove, mock_exists):
        """Test removing non-existent checkpoint."""
        mock_exists.return_value = False

        self.file_manager.remove_checkpoint('test_checkpoint.pkl')

        mock_remove.assert_not_called()

    def test_has_error_content(self):
        """Test error content detection."""
        # Test content with errors
        self.assertTrue(self.file_manager.has_error_content("An internal error has occurred"))
        self.assertTrue(self.file_manager.has_error_content("500 Internal Server Error"))
        self.assertTrue(self.file_manager.has_error_content("Error processing"))

        # Test content without errors
        self.assertFalse(self.file_manager.has_error_content("Normal response content"))
        self.assertFalse(self.file_manager.has_error_content("Processing completed successfully"))

    def test_scan_for_error_files_no_output_dir(self):
        """Test scanning for error files when output directory doesn't exist."""
        # Use non-existent directory
        fm = FileManager(self.input_dir, "/non/existent/path")

        error_files = fm.scan_for_error_files()

        self.assertEqual(error_files, [])

    def test_scan_for_error_files_with_errors(self):
        """Test scanning for error files with actual error content."""
        # Create test files
        good_file = os.path.join(self.output_dir, "good.txt")
        error_file = os.path.join(self.output_dir, "error.txt")

        with open(good_file, 'w') as f:
            f.write("Normal caption content")

        with open(error_file, 'w') as f:
            f.write("An internal error has occurred")

        with patch('logging.info'):
            error_files = self.file_manager.scan_for_error_files()

        self.assertEqual(len(error_files), 1)
        self.assertIn(error_file, error_files)

    def test_scan_for_error_files_unreadable(self):
        """Test scanning for error files with unreadable files."""
        # Create test file
        test_file = os.path.join(self.output_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test content")

        # Mock file reading to raise exception
        with patch('builtins.open', side_effect=PermissionError("Cannot read file")):
            with patch('logging.info'), patch('logging.warning'):
                error_files = self.file_manager.scan_for_error_files()

        self.assertEqual(len(error_files), 1)
        self.assertIn(test_file, error_files)

    def test_get_image_files(self):
        """Test getting image files from input directory."""
        # Create test image files
        test_files = ['image1.jpg', 'image2.png', 'document.txt', 'image3.gif']
        for filename in test_files:
            filepath = os.path.join(self.input_dir, filename)
            with open(filepath, 'w') as f:
                f.write("test content")

        image_files = self.file_manager.get_image_files()

        # Should only return image files
        image_filenames = [os.path.basename(f) for f in image_files]
        self.assertIn('image1.jpg', image_filenames)
        self.assertIn('image2.png', image_filenames)
        self.assertIn('image3.gif', image_filenames)
        self.assertNotIn('document.txt', image_filenames)

    def test_count_total_files(self):
        """Test counting total image files."""
        # Create test files
        test_files = ['image1.jpg', 'image2.png', 'document.txt', 'image3.gif']
        for filename in test_files:
            filepath = os.path.join(self.input_dir, filename)
            with open(filepath, 'w') as f:
                f.write("test content")

        total = self.file_manager.count_total_files()

        # Should count only image files (3 out of 4)
        self.assertEqual(total, 3)

    def test_get_pending_files(self):
        """Test getting pending files for processing."""
        # Create test image files
        test_files = ['image1.jpg', 'image2.png', 'image3.gif']
        for filename in test_files:
            filepath = os.path.join(self.input_dir, filename)
            with open(filepath, 'w') as f:
                f.write("test content")

        # Mark one file as processed
        processed_files = {'image1.jpg'}

        with patch('os.makedirs'):
            pending_files = self.file_manager.get_pending_files(processed_files)

        # Should return 2 pending files
        self.assertEqual(len(pending_files), 2)

        pending_names = [os.path.basename(f['input_path']) for f in pending_files]
        self.assertIn('image2.png', pending_names)
        self.assertIn('image3.gif', pending_names)
        self.assertNotIn('image1.jpg', pending_names)

    @patch.object(FileManager, 'scan_for_error_files')
    @patch('os.path.exists')
    def test_get_error_file_inputs(self, mock_exists, mock_scan):
        """Test getting input files corresponding to error outputs."""
        # Setup mock error files
        error_file = os.path.join(self.output_dir, "subdir", "error.txt")
        mock_scan.return_value = [error_file]

        # Mock file existence check
        input_file = os.path.join(self.input_dir, "subdir", "error.jpg")
        mock_exists.side_effect = lambda path: path == input_file

        with patch('logging.warning'):
            input_files = self.file_manager.get_error_file_inputs()

        self.assertEqual(len(input_files), 1)
        self.assertEqual(input_files[0]['input_path'], input_file)
        self.assertEqual(input_files[0]['output_path'], error_file)

    def test_prepare_image_tasks(self):
        """Test preparing image processing tasks."""
        file_list = [
            {
                'input_path': 'input1.jpg',
                'output_path': 'output1.txt'
            },
            {
                'input_path': 'input2.jpg',
                'output_path': 'output2.txt'
            }
        ]

        processed_files = set()
        checkpoint_file = 'checkpoint.pkl'
        pbar = Mock()

        tasks = self.file_manager.prepare_image_tasks(
            file_list, processed_files, checkpoint_file, pbar
        )

        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0]['input_path'], 'input1.jpg')
        self.assertEqual(tasks[0]['output_path'], 'output1.txt')
        self.assertEqual(tasks[0]['processed_files'], processed_files)
        self.assertEqual(tasks[0]['checkpoint_file'], checkpoint_file)
        self.assertEqual(tasks[0]['pbar'], pbar)

    @patch.object(FileManager, 'scan_for_error_files')
    @patch.object(FileManager, 'save_checkpoint')
    def test_mark_error_files_for_retry(self, mock_save, mock_scan):
        """Test marking error files for retry."""
        # Setup mock error files
        error_file = os.path.join(self.output_dir, "error.txt")
        mock_scan.return_value = [error_file]

        # Setup processed files
        processed_files = {'error.jpg', 'good.jpg'}

        with patch('logging.info'):
            self.file_manager.mark_error_files_for_retry(processed_files, 'checkpoint.pkl')

        # Should remove error file from processed files
        self.assertNotIn('error.jpg', processed_files)
        self.assertIn('good.jpg', processed_files)

        # Should save updated checkpoint
        mock_save.assert_called_once_with(processed_files, 'checkpoint.pkl')


if __name__ == '__main__':
    unittest.main()
