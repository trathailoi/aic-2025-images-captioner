"""
Unit tests for main module.
"""

import unittest
import sys
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import main


class TestMain(unittest.TestCase):
    """Test main module functions."""

    def test_signal_handler(self):
        """Test signal handler sets shutdown flag."""
        # Reset shutdown flag
        main.shutdown_requested = False

        with patch('logging.info') as mock_log:
            main.signal_handler(2, None)  # SIGINT

        self.assertTrue(main.shutdown_requested)
        self.assertEqual(mock_log.call_count, 2)

    @patch('signal.signal')
    def test_setup_signal_handlers(self, mock_signal):
        """Test signal handlers are registered."""
        main.setup_signal_handlers()

        # Should register both SIGINT and SIGTERM
        self.assertEqual(mock_signal.call_count, 2)

    @patch('sys.exit')
    @patch('logging.error')
    def test_validate_api_keys_empty(self, mock_log_error, mock_sys_exit):
        """Test validation fails with empty API keys."""
        with patch('main.GENAI_API_KEYS', []):
            main.validate_api_keys()

        mock_log_error.assert_called_once()
        mock_sys_exit.assert_called_once_with(1)

    @patch('sys.exit')
    @patch('logging.error')
    def test_validate_api_keys_none(self, mock_log_error, mock_sys_exit):
        """Test validation fails with None API keys."""
        with patch('main.GENAI_API_KEYS', None):
            main.validate_api_keys()

        mock_log_error.assert_called_once()
        mock_sys_exit.assert_called_once_with(1)

    def test_validate_api_keys_valid(self):
        """Test validation passes with valid API keys."""
        with patch('main.GENAI_API_KEYS', ['key1', 'key2']):
            # Should not raise exception or exit
            main.validate_api_keys()

    @patch('main.FileManager')
    @patch('main.GeminiClient')
    @patch('main.ImageProcessor')
    @patch('logging.info')
    def test_process_directory_all_processed(self, mock_log, mock_image_processor_class, mock_gemini_client_class, mock_file_manager_class):
        """Test process_directory when all files are already processed."""
        # Setup mocks
        mock_file_manager = Mock()
        mock_file_manager.load_checkpoint.return_value = {'file1.jpg', 'file2.jpg'}
        mock_file_manager.count_total_files.return_value = 2
        mock_file_manager_class.return_value = mock_file_manager

        # Test
        main.process_directory()

        # Should log completion message and return early
        mock_log.assert_any_call("🎉 All files have been processed!")

    @patch('main.FileManager')
    @patch('main.GeminiClient')
    @patch('main.ImageProcessor')
    @patch('main.tqdm')
    @patch('logging.info')
    def test_process_directory_with_pending_files(self, mock_log, mock_tqdm, mock_image_processor_class, mock_gemini_client_class, mock_file_manager_class):
        """Test process_directory with pending files."""
        # Setup mocks
        mock_file_manager = Mock()
        mock_file_manager.load_checkpoint.return_value = set()
        mock_file_manager.count_total_files.return_value = 2
        mock_file_manager.get_pending_files.return_value = [
            {'input_path': 'input1.jpg', 'output_path': 'output1.txt'},
            {'input_path': 'input2.jpg', 'output_path': 'output2.txt'}
        ]
        mock_file_manager.prepare_image_tasks.return_value = []
        mock_file_manager.scan_for_error_files.return_value = []
        mock_file_manager_class.return_value = mock_file_manager

        mock_gemini_client = Mock()
        mock_gemini_client_class.return_value = mock_gemini_client

        mock_image_processor = Mock()
        mock_image_processor_class.return_value = mock_image_processor

        mock_pbar = Mock()
        mock_tqdm.return_value.__enter__.return_value = mock_pbar

        # Reset shutdown flag
        main.shutdown_requested = False

        # Test
        main.process_directory()

        # Verify components were created and used
        mock_file_manager_class.assert_called_once()
        mock_gemini_client_class.assert_called_once()
        mock_image_processor_class.assert_called_once_with(mock_gemini_client)

        # Verify processing was attempted
        mock_image_processor.process_images_batch.assert_called_once()
        mock_image_processor.log_stats.assert_called_once()

    @patch('main.FileManager')
    @patch('main.GeminiClient')
    @patch('main.ImageProcessor')
    @patch('logging.info')
    def test_fix_error_files_no_errors(self, mock_log, mock_image_processor_class, mock_gemini_client_class, mock_file_manager_class):
        """Test fix_error_files when no error files exist."""
        # Setup mocks
        mock_file_manager = Mock()
        mock_file_manager.get_error_file_inputs.return_value = []
        mock_file_manager_class.return_value = mock_file_manager

        # Test
        main.fix_error_files()

        # Should log no errors found and return early
        mock_log.assert_any_call("✅ No error files found to fix.")

    @patch('main.FileManager')
    @patch('main.GeminiClient')
    @patch('main.ImageProcessor')
    @patch('main.tqdm')
    @patch('logging.info')
    def test_fix_error_files_with_errors(self, mock_log, mock_tqdm, mock_image_processor_class, mock_gemini_client_class, mock_file_manager_class):
        """Test fix_error_files with actual error files."""
        # Setup mocks
        mock_file_manager = Mock()
        mock_file_manager.get_error_file_inputs.return_value = [
            {'input_path': 'error1.jpg', 'output_path': 'error1.txt'},
            {'input_path': 'error2.jpg', 'output_path': 'error2.txt'}
        ]
        mock_file_manager.prepare_image_tasks.return_value = []
        mock_file_manager.scan_for_error_files.return_value = []
        mock_file_manager_class.return_value = mock_file_manager

        mock_gemini_client = Mock()
        mock_gemini_client_class.return_value = mock_gemini_client

        mock_image_processor = Mock()
        mock_image_processor_class.return_value = mock_image_processor

        mock_pbar = Mock()
        mock_tqdm.return_value.__enter__.return_value = mock_pbar

        # Reset shutdown flag
        main.shutdown_requested = False

        # Test
        main.fix_error_files()

        # Verify processing was attempted
        mock_image_processor.process_images_batch.assert_called_once()
        mock_image_processor.log_stats.assert_called_once()

    @patch('main.setup_signal_handlers')
    @patch('main.validate_api_keys')
    @patch('main.parse_arguments')
    @patch('main.GeminiClient')
    @patch('sys.exit')
    def test_main_show_key_stats(self, mock_sys_exit, mock_gemini_client_class, mock_parse_args, mock_validate, mock_setup_signals):
        """Test main function with --show-key-stats flag."""
        # Setup mocks
        mock_args = Mock()
        mock_args.show_key_stats = True
        mock_parse_args.return_value = mock_args

        mock_gemini_client = Mock()
        mock_gemini_client_class.return_value = mock_gemini_client

        # Test
        main.main()

        # Should show stats and exit
        mock_gemini_client.log_key_stats.assert_called_once()
        mock_sys_exit.assert_called_once_with(0)

    @patch('main.setup_signal_handlers')
    @patch('main.validate_api_keys')
    @patch('main.parse_arguments')
    @patch('main.fix_error_files')
    @patch('logging.info')
    def test_main_fix_mode(self, mock_log, mock_fix_error_files, mock_parse_args, mock_validate, mock_setup_signals):
        """Test main function in fix mode."""
        # Setup mocks
        mock_args = Mock()
        mock_args.show_key_stats = False
        mock_args.fix = True
        mock_args.max_workers = 5
        mock_args.retries = 10
        mock_parse_args.return_value = mock_args

        # Reset shutdown flag
        main.shutdown_requested = False

        # Test
        main.main()

        # Should call fix_error_files
        mock_fix_error_files.assert_called_once_with(max_workers=5, max_retries=10)

    @patch('main.setup_signal_handlers')
    @patch('main.validate_api_keys')
    @patch('main.parse_arguments')
    @patch('main.process_directory')
    @patch('logging.info')
    def test_main_normal_mode(self, mock_log, mock_process_directory, mock_parse_args, mock_validate, mock_setup_signals):
        """Test main function in normal processing mode."""
        # Setup mocks
        mock_args = Mock()
        mock_args.show_key_stats = False
        mock_args.fix = False
        mock_args.max_workers = 5
        mock_args.no_retry_errors = False
        mock_args.retries = 10
        mock_args.key_rotation_delay = 1.5
        mock_parse_args.return_value = mock_args

        # Reset shutdown flag
        main.shutdown_requested = False

        # Test
        main.main()

        # Should call process_directory
        mock_process_directory.assert_called_once_with(
            max_workers=5,
            retry_errors=True,  # Should be inverted from no_retry_errors
            max_retries=10,
            key_rotation_delay=1.5
        )

    @patch('main.setup_signal_handlers')
    @patch('main.validate_api_keys')
    @patch('main.parse_arguments')
    @patch('main.process_directory')
    @patch('logging.info')
    @patch('sys.exit')
    def test_main_keyboard_interrupt(self, mock_sys_exit, mock_log, mock_process_directory, mock_parse_args, mock_validate, mock_setup_signals):
        """Test main function with keyboard interrupt."""
        # Setup mocks
        mock_args = Mock()
        mock_args.show_key_stats = False
        mock_args.fix = False
        mock_parse_args.return_value = mock_args

        mock_process_directory.side_effect = KeyboardInterrupt()

        # Test
        main.main()

        # Should handle interrupt gracefully
        mock_log.assert_any_call("🛑 Process interrupted by user")
        mock_sys_exit.assert_called_once_with(0)

    @patch('main.setup_signal_handlers')
    @patch('main.validate_api_keys')
    @patch('main.parse_arguments')
    @patch('main.process_directory')
    @patch('logging.error')
    @patch('sys.exit')
    def test_main_unexpected_exception(self, mock_sys_exit, mock_log_error, mock_process_directory, mock_parse_args, mock_validate, mock_setup_signals):
        """Test main function with unexpected exception."""
        # Setup mocks
        mock_args = Mock()
        mock_args.show_key_stats = False
        mock_args.fix = False
        mock_parse_args.return_value = mock_args

        mock_process_directory.side_effect = Exception("Unexpected error")

        # Test
        main.main()

        # Should handle exception gracefully
        mock_log_error.assert_any_call("💥 Unexpected error: Unexpected error")
        mock_sys_exit.assert_called_once_with(1)


if __name__ == '__main__':
    unittest.main()
