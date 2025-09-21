"""
Gemini API client module with key rotation and rate limiting.
Handles all interactions with the Google GenAI API.
"""

import json
import time
import random
import threading
import logging
from functools import wraps

from google import genai
from google.genai import types

from .config import (
    GENAI_API_KEYS, SAFETY_SETTINGS, PROMPT, RATE_LIMIT_MESSAGES,
    DEFAULT_RATE_LIMIT_CALLS, DEFAULT_RATE_LIMIT_PERIOD
)


class RateLimiter:
    """Rate limiter decorator for API calls."""

    def __init__(self, max_calls=DEFAULT_RATE_LIMIT_CALLS, period=DEFAULT_RATE_LIMIT_PERIOD):
        self.max_calls = max_calls
        self.period = period
        self.calls = []
        self.lock = threading.Lock()

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self.lock:
                now = time.time()
                self.calls = [call for call in self.calls if call > now - self.period]
                if len(self.calls) >= self.max_calls:
                    sleep_time = self.calls[0] - (now - self.period)
                    time.sleep(sleep_time)
                self.calls.append(time.time())
            return func(*args, **kwargs)
        return wrapper


class GeminiClient:
    """Manages Gemini API client with key rotation and error handling."""

    def __init__(self, api_keys=None):
        """Initialize with API keys."""
        self.api_keys = api_keys or GENAI_API_KEYS
        if not self.api_keys or not any(self.api_keys):
            raise ValueError("No valid GenAI API keys found.")

        self.current_key_index = 0
        self.key_rotation_lock = threading.Lock()
        self.key_stats = {i: {'requests': 0, 'errors': 0, 'rate_limits': 0}
                         for i in range(len(self.api_keys))}

        # Initialize with first key
        self.client = genai.Client(api_key=self.api_keys[self.current_key_index])
        logging.info(f"🔑 Initialized with API key #{self.current_key_index + 1} "
                    f"(...{self.api_keys[self.current_key_index][-4:]})")

    def rotate_api_key(self):
        """Rotate to the next available API key."""
        with self.key_rotation_lock:
            old_index = self.current_key_index
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)

            # Update client with new key
            self.client = genai.Client(api_key=self.api_keys[self.current_key_index])

            # Log the rotation
            logging.info(f"🔄 Rotated API key: #{old_index + 1} → #{self.current_key_index + 1} "
                        f"(...{self.api_keys[self.current_key_index][-4:]})")

            return self.current_key_index

    def is_rate_limit_error(self, error_str):
        """Check if error is related to rate limiting or quota."""
        error_lower = error_str.lower()
        return any(rate_msg.lower() in error_lower for rate_msg in RATE_LIMIT_MESSAGES)

    def exponential_backoff_with_jitter(self, attempt, base_delay=1, max_delay=60, jitter=True):
        """Calculate delay for exponential backoff with optional jitter."""
        delay = min(base_delay * (2 ** attempt), max_delay)
        if jitter:
            # Add ±25% jitter to prevent synchronized retries
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
        return max(delay, 0.1)  # Ensure minimum delay

    def log_key_stats(self):
        """Log current statistics for all API keys."""
        logging.info("�� API Key Statistics:")
        for i, stats in self.key_stats.items():
            total = stats['requests']
            errors = stats['errors']
            rate_limits = stats['rate_limits']
            success_rate = ((total - errors) / total * 100) if total > 0 else 0
            current_marker = " ← CURRENT" if i == self.current_key_index else ""
            logging.info(f"   Key #{i+1}: {total} requests, {errors} errors, "
                        f"{rate_limits} rate limits, {success_rate:.1f}% success{current_marker}")

    @RateLimiter(max_calls=DEFAULT_RATE_LIMIT_CALLS, period=DEFAULT_RATE_LIMIT_PERIOD)
    def process_image_with_gemini(self, image_path, max_retries=5, key_rotation_delay=1.0):
        """Process image using Gemini API with key rotation on rate limits."""
        time.sleep(2)
        keys_tried = set()
        original_key_index = self.current_key_index

        for attempt in range(max_retries + 1):
            try:
                # Track request for current key
                with self.key_rotation_lock:
                    self.key_stats[self.current_key_index]['requests'] += 1

                with open(image_path, 'rb') as f:
                    image_bytes = f.read()

                # Create image part using new API
                image_part = types.Part.from_bytes(
                    data=image_bytes,
                    mime_type='image/jpeg'
                )

                # Generate content with safety settings
                response = self.client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[PROMPT, image_part],
                    config=types.GenerateContentConfig(
                        safety_settings=SAFETY_SETTINGS
                    )
                )

                # Check if response has valid parts before accessing text
                if not response.candidates:
                    with self.key_rotation_lock:
                        self.key_stats[self.current_key_index]['errors'] += 1
                    return json.dumps({"error": f"No candidates returned for {image_path}"})

                candidate = response.candidates[0]

                # Check finish reason
                if candidate.finish_reason == types.FinishReason.STOP:
                    # Normal completion - success!
                    if candidate.content and candidate.content.parts:
                        return candidate.content.parts[0].text
                    else:
                        with self.key_rotation_lock:
                            self.key_stats[self.current_key_index]['errors'] += 1
                        return json.dumps({"error": f"No content parts in response for {image_path}"})
                elif candidate.finish_reason == types.FinishReason.SAFETY:
                    with self.key_rotation_lock:
                        self.key_stats[self.current_key_index]['errors'] += 1
                    return json.dumps({"error": f"Content blocked by safety filters for {image_path}"})
                elif candidate.finish_reason == types.FinishReason.MAX_TOKENS:
                    with self.key_rotation_lock:
                        self.key_stats[self.current_key_index]['errors'] += 1
                    return json.dumps({"error": f"Response truncated due to max tokens for {image_path}"})
                else:
                    with self.key_rotation_lock:
                        self.key_stats[self.current_key_index]['errors'] += 1
                    return json.dumps({"error": f"Unexpected finish reason {candidate.finish_reason} for {image_path}"})

            except Exception as e:
                error_str = str(e)

                # Track error for current key
                with self.key_rotation_lock:
                    self.key_stats[self.current_key_index]['errors'] += 1

                # Check if this is a rate limit error
                if self.is_rate_limit_error(error_str):
                    with self.key_rotation_lock:
                        self.key_stats[self.current_key_index]['rate_limits'] += 1

                    keys_tried.add(self.current_key_index)

                    # If we haven't tried all keys yet, rotate and try immediately
                    if len(keys_tried) < len(self.api_keys):
                        logging.warning(f"🚦 Rate limit hit on key #{self.current_key_index + 1} for {image_path}")
                        self.rotate_api_key()
                        if key_rotation_delay > 0:
                            time.sleep(key_rotation_delay)
                        continue  # Try with new key immediately (don't count as retry)
                    else:
                        # All keys exhausted
                        logging.error(f"❌ All {len(self.api_keys)} API keys rate limited for {image_path}")
                        return json.dumps({"error": f"All API keys rate limited for {image_path}: {error_str}"})

                # Check if this is a retryable server error (non-rate-limit)
                is_retryable = any(error_code in error_str for error_code in ['500', '503', 'INTERNAL', 'UNAVAILABLE', 'Server is overloaded'])

                if is_retryable and attempt < max_retries:
                    delay = self.exponential_backoff_with_jitter(attempt)
                    logging.warning(f"🔄 Gemini API error (attempt {attempt + 1}/{max_retries + 1}) "
                                  f"on key #{self.current_key_index + 1} for {image_path}: {error_str}")
                    logging.info(f"⏱️  Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    continue
                else:
                    # Non-retryable error or max retries reached
                    if attempt >= max_retries:
                        logging.error(f"❌ Max retries ({max_retries}) reached for {image_path}: {error_str}")
                    else:
                        logging.error(f"❌ Non-retryable error for {image_path}: {error_str}")
                    return json.dumps({"error": f"Error processing with Gemini {image_path}: {error_str}"})

        # Should never reach here, but just in case
        return json.dumps({"error": f"Unexpected error in retry loop for {image_path}"})
