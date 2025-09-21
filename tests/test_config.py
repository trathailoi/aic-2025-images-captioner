"""
Unit tests for config module.
"""

import unittest
import argparse
from unittest.mock import patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src import config


class TestConfig(unittest.TestCase):
    """Test configuration module."""

    def test_api_keys_exist(self):
        """Test that API keys are defined."""
        self.assertIsInstance(config.GENAI_API_KEYS, list)
        self.assertGreater(len(config.GENAI_API_KEYS), 0)
        for key in config.GENAI_API_KEYS:
            self.assertIsInstance(key, str)
            self.assertGreater(len(key), 0)

    def test_directories_defined(self):
        """Test that input and output directories are defined."""
        self.assertIsInstance(config.INPUT_DIR, str)
        self.assertIsInstance(config.OUTPUT_DIR, str)
        self.assertGreater(len(config.INPUT_DIR), 0)
        self.assertGreater(len(config.OUTPUT_DIR), 0)

    def test_error_messages_defined(self):
        """Test that error message patterns are defined."""
        self.assertIsInstance(config.ERROR_MESSAGES, list)
        self.assertGreater(len(config.ERROR_MESSAGES), 0)
        for msg in config.ERROR_MESSAGES:
            self.assertIsInstance(msg, str)

    def test_rate_limit_messages_defined(self):
        """Test that rate limit message patterns are defined."""
        self.assertIsInstance(config.RATE_LIMIT_MESSAGES, list)
        self.assertGreater(len(config.RATE_LIMIT_MESSAGES), 0)
        for msg in config.RATE_LIMIT_MESSAGES:
            self.assertIsInstance(msg, str)

    def test_safety_settings_defined(self):
        """Test that safety settings are defined."""
        self.assertIsInstance(config.SAFETY_SETTINGS, list)
        self.assertGreater(len(config.SAFETY_SETTINGS), 0)

    def test_image_extensions_defined(self):
        """Test that image extensions are defined."""
        self.assertIsInstance(config.IMAGE_EXTENSIONS, tuple)
        self.assertGreater(len(config.IMAGE_EXTENSIONS), 0)
        for ext in config.IMAGE_EXTENSIONS:
            self.assertIsInstance(ext, str)
            self.assertTrue(ext.startswith('.'))

    def test_default_values(self):
        """Test that default configuration values are reasonable."""
        self.assertIsInstance(config.DEFAULT_MAX_WORKERS, int)
        self.assertGreater(config.DEFAULT_MAX_WORKERS, 0)

        self.assertIsInstance(config.DEFAULT_MAX_RETRIES, int)
        self.assertGreater(config.DEFAULT_MAX_RETRIES, 0)

        self.assertIsInstance(config.DEFAULT_KEY_ROTATION_DELAY, (int, float))
        self.assertGreaterEqual(config.DEFAULT_KEY_ROTATION_DELAY, 0)

    def test_prompt_defined(self):
        """Test that the prompt is defined and not empty."""
        self.assertIsInstance(config.PROMPT, str)
        self.assertGreater(len(config.PROMPT), 100)  # Should be substantial
        self.assertIn("JSON", config.PROMPT)  # Should contain JSON format instructions

    def test_parse_arguments_default(self):
        """Test argument parsing with default values."""
        with patch('sys.argv', ['script.py']):
            args = config.parse_arguments()
            self.assertEqual(args.max_workers, config.DEFAULT_MAX_WORKERS)
            self.assertEqual(args.retries, config.DEFAULT_MAX_RETRIES)
            self.assertEqual(args.key_rotation_delay, config.DEFAULT_KEY_ROTATION_DELAY)
            self.assertFalse(args.fix)
            self.assertFalse(args.no_retry_errors)
            self.assertFalse(args.show_key_stats)

    def test_parse_arguments_custom(self):
        """Test argument parsing with custom values."""
        with patch('sys.argv', ['script.py', '--fix', '--max_workers', '5', '--retries', '10', '--key-rotation-delay', '2.5', '--no-retry-errors', '--show-key-stats']):
            args = config.parse_arguments()
            self.assertTrue(args.fix)
            self.assertEqual(args.max_workers, 5)
            self.assertEqual(args.retries, 10)
            self.assertEqual(args.key_rotation_delay, 2.5)
            self.assertTrue(args.no_retry_errors)
            self.assertTrue(args.show_key_stats)


if __name__ == '__main__':
    unittest.main()
