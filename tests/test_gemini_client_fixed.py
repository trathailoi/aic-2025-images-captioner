"""
Unit tests for gemini_client module (fixed version).
"""

import unittest
import json
import threading
import time
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.gemini_client import GeminiClient, RateLimiter


class TestRateLimiter(unittest.TestCase):
    """Test RateLimiter class."""

    def test_rate_limiter_init(self):
        """Test RateLimiter initialization."""
        limiter = RateLimiter(max_calls=10, period=60)
        self.assertEqual(limiter.max_calls, 10)
        self.assertEqual(limiter.period, 60)
        self.assertEqual(len(limiter.calls), 0)
        self.assertTrue(hasattr(limiter, 'lock'))

    def test_rate_limiter_decorator(self):
        """Test RateLimiter as decorator."""
        @RateLimiter(max_calls=2, period=1)
        def test_func():
            return "called"

        # Should allow first two calls
        result1 = test_func()
        result2 = test_func()
        self.assertEqual(result1, "called")
        self.assertEqual(result2, "called")


class TestGeminiClient(unittest.TestCase):
    """Test GeminiClient class."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_api_keys = ['test_key_1', 'test_key_2', 'test_key_3']

    @patch('gemini_client.genai.Client')
    def test_init_valid_keys(self, mock_genai_client):
        """Test initialization with valid API keys."""
        client = GeminiClient(api_keys=self.test_api_keys)
        self.assertEqual(client.api_keys, self.test_api_keys)
        self.assertEqual(client.current_key_index, 0)
        self.assertTrue(hasattr(client, 'key_rotation_lock'))
        self.assertEqual(len(client.key_stats), 3)

    @patch('gemini_client.GENAI_API_KEYS', [])
    def test_init_no_keys(self):
        """Test initialization with no API keys raises ValueError."""
        with self.assertRaises(ValueError):
            GeminiClient(api_keys=[])

        with self.assertRaises(ValueError):
            GeminiClient(api_keys=None)

        with self.assertRaises(ValueError):
            GeminiClient(api_keys=[""])

    @patch('gemini_client.genai.Client')
    def test_rotate_api_key(self, mock_genai_client):
        """Test API key rotation."""
        client = GeminiClient(api_keys=self.test_api_keys)

        # Test rotation from 0 to 1
        self.assertEqual(client.current_key_index, 0)
        new_index = client.rotate_api_key()
        self.assertEqual(new_index, 1)
        self.assertEqual(client.current_key_index, 1)

        # Test rotation from 2 to 0 (wrap around)
        client.current_key_index = 2
        new_index = client.rotate_api_key()
        self.assertEqual(new_index, 0)
        self.assertEqual(client.current_key_index, 0)

    @patch('gemini_client.genai.Client')
    def test_is_rate_limit_error(self, mock_genai_client):
        """Test rate limit error detection."""
        client = GeminiClient(api_keys=self.test_api_keys)

        # Test rate limit errors
        self.assertTrue(client.is_rate_limit_error("Error code: 429"))
        self.assertTrue(client.is_rate_limit_error("insufficient_quota"))
        self.assertTrue(client.is_rate_limit_error("Rate limit exceeded"))
        self.assertTrue(client.is_rate_limit_error("RESOURCE_EXHAUSTED"))

        # Test non-rate limit errors
        self.assertFalse(client.is_rate_limit_error("500 Internal Server Error"))
        self.assertFalse(client.is_rate_limit_error("Connection timeout"))
        self.assertFalse(client.is_rate_limit_error("Invalid request"))

    @patch('gemini_client.genai.Client')
    def test_exponential_backoff_with_jitter(self, mock_genai_client):
        """Test exponential backoff calculation."""
        client = GeminiClient(api_keys=self.test_api_keys)

        # Test without jitter
        delay0 = client.exponential_backoff_with_jitter(0, base_delay=1, jitter=False)
        delay1 = client.exponential_backoff_with_jitter(1, base_delay=1, jitter=False)
        delay2 = client.exponential_backoff_with_jitter(2, base_delay=1, jitter=False)

        self.assertEqual(delay0, 1)
        self.assertEqual(delay1, 2)
        self.assertEqual(delay2, 4)

        # Test with max delay
        delay_max = client.exponential_backoff_with_jitter(10, base_delay=1, max_delay=5, jitter=False)
        self.assertEqual(delay_max, 5)

        # Test with jitter (should be different and within range)
        delay_jitter1 = client.exponential_backoff_with_jitter(2, base_delay=1, jitter=True)

        # Should be around 4 ± 25%
        self.assertGreaterEqual(delay_jitter1, 0.1)  # Minimum delay
        self.assertLessEqual(delay_jitter1, 5)  # 4 + 1 (25% jitter)

    @patch('gemini_client.genai.Client')
    def test_log_key_stats(self, mock_genai_client):
        """Test key statistics logging."""
        client = GeminiClient(api_keys=self.test_api_keys)

        # Update some stats
        client.key_stats[0]['requests'] = 10
        client.key_stats[0]['errors'] = 2
        client.key_stats[1]['requests'] = 5
        client.key_stats[1]['rate_limits'] = 1

        # Should not raise exception
        with patch('logging.info') as mock_log:
            client.log_key_stats()
            self.assertTrue(mock_log.called)

    @patch('gemini_client.genai.Client')
    @patch('builtins.open', create=True)
    @patch('gemini_client.types')
    def test_process_image_success(self, mock_types, mock_open, mock_genai_client):
        """Test successful image processing."""
        # Setup mocks
        mock_file_content = b"fake_image_data"
        mock_open.return_value.__enter__.return_value.read.return_value = mock_file_content

        # Mock response
        mock_candidate = Mock()
        mock_candidate.finish_reason = mock_types.FinishReason.STOP
        mock_candidate.content.parts = [Mock()]
        mock_candidate.content.parts[0].text = "Test response"

        mock_response = Mock()
        mock_response.candidates = [mock_candidate]

        mock_client_instance = Mock()
        mock_client_instance.models.generate_content.return_value = mock_response
        mock_genai_client.return_value = mock_client_instance

        # Test
        client = GeminiClient(api_keys=self.test_api_keys)
        client.client = mock_client_instance

        result = client.process_image_with_gemini("test_image.jpg", max_retries=1)

        self.assertEqual(result, "Test response")
        mock_open.assert_called_once_with("test_image.jpg", 'rb')

    @patch('gemini_client.genai.Client')
    @patch('builtins.open', create=True)
    @patch('gemini_client.types')
    def test_process_image_no_candidates(self, mock_types, mock_open, mock_genai_client):
        """Test image processing with no candidates returned."""
        # Setup mocks
        mock_file_content = b"fake_image_data"
        mock_open.return_value.__enter__.return_value.read.return_value = mock_file_content

        mock_response = Mock()
        mock_response.candidates = []

        mock_client_instance = Mock()
        mock_client_instance.models.generate_content.return_value = mock_response
        mock_genai_client.return_value = mock_client_instance

        # Test
        client = GeminiClient(api_keys=self.test_api_keys)
        client.client = mock_client_instance

        result = client.process_image_with_gemini("test_image.jpg", max_retries=1)

        # Should return error JSON
        result_dict = json.loads(result)
        self.assertIn("error", result_dict)
        self.assertIn("No candidates returned", result_dict["error"])


if __name__ == '__main__':
    unittest.main()
