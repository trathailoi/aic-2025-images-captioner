"""
Gemini Image Captioner - A modular image captioning system using Google's Gemini API.

This package provides a complete solution for batch processing images with AI-generated
captions in Vietnamese, featuring error recovery, checkpoint management, and API key rotation.
"""

__version__ = "2.0.0"
__author__ = "Refactored by Claude"

from .config import *
from .gemini_client import GeminiClient
from .image_processor import ImageProcessor
from .file_manager import FileManager

__all__ = [
    'GeminiClient',
    'ImageProcessor',
    'FileManager',
    # Configuration exports
    'GENAI_API_KEYS',
    'INPUT_DIR',
    'OUTPUT_DIR',
    'parse_arguments'
]
