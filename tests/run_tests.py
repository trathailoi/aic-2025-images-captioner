#!/usr/bin/env python3
"""
Test runner for the refactored Gemini Image Captioner.
Runs all unit tests and provides a summary.
"""

import unittest
import sys
import os

def discover_and_run_tests():
    """Discover and run all tests in the current directory."""
    # Discover all test files
    loader = unittest.TestLoader()
    start_dir = os.path.dirname(os.path.abspath(__file__))
    suite = loader.discover(start_dir, pattern='test_*.py')

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")

    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")

    # Return success/failure
    return result.wasSuccessful()

if __name__ == '__main__':
    success = discover_and_run_tests()
    sys.exit(0 if success else 1)
