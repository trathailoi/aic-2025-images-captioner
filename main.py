"""
Main application entry point for Gemini Image Captioner.
Handles CLI interface, signal handling, and orchestrates the processing workflow.
"""

import sys
import logging
import signal
from tqdm import tqdm

from src.config import parse_arguments, GENAI_API_KEYS, OUTPUT_DIR
from src.gemini_client import GeminiClient
from src.image_processor import ImageProcessor
from src.file_manager import FileManager


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle CTRL+C and other termination signals gracefully."""
    global shutdown_requested
    shutdown_requested = True
    logging.info("\n🛑 Shutdown requested. Waiting for current tasks to complete...")
    logging.info("📝 Progress will be saved. You can resume later by running the script again.")


def setup_signal_handlers():
    """Register signal handlers for graceful shutdown."""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def validate_api_keys():
    """Validate that API keys are available."""
    if not GENAI_API_KEYS or not any(GENAI_API_KEYS):
        logging.error("No valid GenAI API keys found.")
        sys.exit(1)


def process_directory(checkpoint_file='checkpoint.pkl', max_workers=10, retry_errors=True, max_retries=5, key_rotation_delay=1.0):
    """Process all images in the input directory."""
    global shutdown_requested

    logging.info(f"🚀 Starting processing with {len(GENAI_API_KEYS)} Gemini API keys")

    # Initialize components
    file_manager = FileManager()
    gemini_client = GeminiClient()
    image_processor = ImageProcessor(gemini_client)

    # Load checkpoint
    processed_files = file_manager.load_checkpoint(checkpoint_file)

    # If retry_errors is True, scan for error files and remove them from processed_files
    if retry_errors:
        file_manager.mark_error_files_for_retry(processed_files, checkpoint_file)

    # Get file counts and remaining work
    total_files = file_manager.count_total_files()
    remaining_files = total_files - len(processed_files)

    logging.info(f"📊 Total files: {total_files}, Already processed: {len(processed_files)}, Remaining: {remaining_files}")

    if remaining_files == 0:
        logging.info("🎉 All files have been processed!")
        return

    # Get pending files to process
    pending_files = file_manager.get_pending_files(processed_files)

    # Process files with progress bar
    with tqdm(total=total_files, initial=len(processed_files), unit='file', desc='Processing', leave=True, ncols=100) as pbar:
        # Prepare tasks
        tasks = file_manager.prepare_image_tasks(pending_files, processed_files, checkpoint_file, pbar)

        # Set shutdown flag on processor
        image_processor.set_shutdown_flag(shutdown_requested)

        # Process images
        image_processor.process_images_batch(tasks, max_workers, max_retries)

    # Log final statistics
    image_processor.log_stats()

    # Final scan for any remaining errors
    if not shutdown_requested:
        error_files = file_manager.scan_for_error_files()
        if error_files:
            logging.warning(f"⚠️  {len(error_files)} files still contain errors after processing. Run with --fix to attempt again.")
        else:
            logging.info("🎉 All files processed successfully without errors!")

        file_manager.remove_checkpoint(checkpoint_file)
    else:
        logging.info("💾 Progress saved. You can resume by running the script again.")


def fix_error_files(max_workers=10, max_retries=5):
    """Fix files that contain errors."""
    global shutdown_requested

    file_manager = FileManager()
    gemini_client = GeminiClient()
    image_processor = ImageProcessor(gemini_client)

    error_file_inputs = file_manager.get_error_file_inputs()

    if not error_file_inputs:
        logging.info("✅ No error files found to fix.")
        return

    logging.info(f"🔧 Attempting to fix {len(error_file_inputs)} files with errors using {len(GENAI_API_KEYS)} Gemini API keys...")

    # Process error files with progress bar
    with tqdm(total=len(error_file_inputs), unit='file', desc='Fixing', ncols=100) as pbar:
        # Prepare tasks (no checkpoint needed for fixing)
        tasks = file_manager.prepare_image_tasks(error_file_inputs, pbar=pbar)

        # Set shutdown flag on processor
        image_processor.set_shutdown_flag(shutdown_requested)

        # Process error files
        image_processor.process_images_batch(tasks, max_workers, max_retries)

    # Log final statistics
    image_processor.log_stats()

    # Final status
    remaining_errors = file_manager.scan_for_error_files()
    if remaining_errors:
        logging.warning(f"⚠️  {len(remaining_errors)} files still contain errors after fixing.")
    else:
        logging.info("🎉 All error files have been successfully fixed!")


def main():
    """Main application entry point."""
    global shutdown_requested

    # Setup
    setup_signal_handlers()
    validate_api_keys()
    args = parse_arguments()

    # Show key statistics if requested
    if args.show_key_stats:
        gemini_client = GeminiClient()
        gemini_client.log_key_stats()
        sys.exit(0)

    # Log configuration
    logging.info(f"🔄 Retry configuration: max {args.retries} retries with exponential backoff")
    logging.info(f"⏱️  Key rotation delay: {args.key_rotation_delay}s")
    logging.info(f"🔑 Available API keys: {len(GENAI_API_KEYS)}")

    try:
        if args.fix:
            fix_error_files(max_workers=args.max_workers, max_retries=args.retries)
        else:
            process_directory(
                max_workers=args.max_workers,
                retry_errors=not args.no_retry_errors,
                max_retries=args.retries,
                key_rotation_delay=args.key_rotation_delay
            )

        if not shutdown_requested:
            print(f"🎉 Processing complete using Gemini API with key rotation. Results saved to {OUTPUT_DIR}")
        else:
            print(f"⏸️  Processing paused. Resume by running the script again.")

    except KeyboardInterrupt:
        logging.info("🛑 Process interrupted by user")
        sys.exit(0)
    except Exception as e:
        logging.error(f"💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
