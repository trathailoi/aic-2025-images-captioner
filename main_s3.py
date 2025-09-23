"""
Main application entry point for Gemini Image Captioner with S3 support.
Handles CLI interface, signal handling, and orchestrates the processing workflow.
"""

import sys
import logging
import signal
from tqdm import tqdm

from src.config import (
    parse_arguments, GENAI_API_KEYS, OUTPUT_DIR, ProcessingMode,
    get_image_list_from_worker_file
)
from src.gemini_client import GeminiClient
from src.image_processor import ImageProcessor
from src.file_manager import FileManager
from src.s3_client import S3Client

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

def is_error_response(caption):
    """Check if the caption response is an error (JSON error format)."""
    if not caption:
        return True
    try:
        import json
        parsed = json.loads(caption)
        return 'error' in parsed
    except (json.JSONDecodeError, TypeError):
        return False

def process_s3_worker_mode(worker_file_path, worker_id, checkpoint_file='checkpoint.pkl', 
                          max_workers=10, retry_errors=True, max_retries=5, key_rotation_delay=1.0):
    """Process images from S3 using worker assignment file."""
    global shutdown_requested
    
    logging.info(f"🔍 Worker Mode: Processing images from {worker_file_path}")
    logging.info(f"👤 Worker ID: {worker_id}")
    
    # Load assigned images from worker file
    try:
        assigned_images = get_image_list_from_worker_file(worker_file_path)
        logging.info(f"📋 Loaded {len(assigned_images)} assigned images from worker file")
    except Exception as e:
        logging.error(f"❌ Failed to load worker file: {e}")
        sys.exit(1)
    
    if not assigned_images:
        logging.warning("⚠️ No images found in worker file!")
        return
    
    # Initialize components
    s3_client = S3Client()
    gemini_client = GeminiClient()
    
    # Load checkpoint to see what we've already processed
    file_manager = FileManager()
    processed_files = file_manager.load_checkpoint(checkpoint_file)
    
    # Filter out already processed images
    remaining_images = []
    for img_key in assigned_images:
        # Convert S3 key to relative path for checkpoint compatibility
        relative_path = img_key.replace('frames/', '')
        if relative_path not in processed_files:
            remaining_images.append(img_key)
    
    logging.info(f"📊 Total assigned: {len(assigned_images)}, Already processed: {len(assigned_images) - len(remaining_images)}, Remaining: {len(remaining_images)}")
    
    if not remaining_images:
        logging.info("🎉 All assigned images have been processed!")
        return
    
    # Process images
    processed_count = 0
    total_assigned = len(assigned_images)
    already_processed = total_assigned - len(remaining_images)
    
    with tqdm(total=total_assigned, initial=already_processed, unit='file', desc=f'Worker {worker_id}', leave=True, ncols=100) as pbar:
        for img_key in remaining_images:
            if shutdown_requested:
                break
                
            try:
                # Convert S3 key to relative path for processing
                relative_path = img_key.replace('frames/', '')
                
                # Download image temporarily
                import tempfile
                import os
                
                with tempfile.NamedTemporaryFile(suffix=os.path.splitext(relative_path)[1], delete=False) as tmp_file:
                    temp_path = tmp_file.name
                
                logging.info(f"🔄 Processing: {img_key}")
                # Download from S3
                if s3_client.download_image(img_key, temp_path):
                    # Process with Gemini
                    caption = gemini_client.process_image_with_gemini(temp_path)
                    
                    # Check if caption is valid (not an error response)
                    if caption and not is_error_response(caption):
                        # Upload caption to S3
                        caption_key = s3_client.get_caption_key_from_image_key(img_key)
                        
                        # Save caption to temp file first
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as caption_file:
                            caption_file.write(caption)
                            caption_temp_path = caption_file.name
                        
                        # Upload to S3
                        if s3_client.upload_caption(caption_temp_path, caption_key):
                            # Mark as processed in checkpoint
                            processed_files.add(relative_path)
                            file_manager.save_checkpoint(processed_files, checkpoint_file)
                            processed_count += 1
                            pbar.update(1)
                            logging.info(f"✅ Processed: {img_key} -> {caption_key}")
                        else:
                            logging.error(f"❌ Failed to upload caption for {img_key}")
                        
                        # Clean up caption temp file
                        os.unlink(caption_temp_path)
                    else:
                        if caption:
                            logging.error(f"❌ Failed to generate caption for {img_key}: {caption}")
                        else:
                            logging.error(f"❌ Failed to generate caption for {img_key}")
                    
                    # Clean up image temp file
                    os.unlink(temp_path)
                else:
                    logging.error(f"❌ Failed to download {img_key}")
                    
            except Exception as e:
                logging.error(f"❌ Error processing {img_key}: {e}")
                continue
    
    logging.info(f"✅ Worker {worker_id} processed {processed_count} new images")
    
    if not shutdown_requested:
        logging.info(f"🎉 Worker {worker_id} completed all assigned work!")
    else:
        logging.info(f"💾 Worker {worker_id} progress saved. Resume by running the same command.")

def process_local_mode(checkpoint_file='checkpoint.pkl', max_workers=10, retry_errors=True, max_retries=5, key_rotation_delay=1.0):
    """Original local filesystem processing mode."""
    global shutdown_requested

    logging.info(f"🚀 Starting local processing with {len(GENAI_API_KEYS)} Gemini API keys")

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
        # Determine processing mode
        processing_mode = args.processing_mode
        
        if processing_mode == ProcessingMode.S3_WORKER:
            # S3 Worker mode
            if not args.worker_file:
                logging.error("❌ Worker file required for S3 worker mode. Use --worker-file option.")
                sys.exit(1)
            
            process_s3_worker_mode(
                worker_file_path=args.worker_file,
                worker_id=args.worker_id,
                max_workers=args.max_workers,
                retry_errors=not args.no_retry_errors,
                max_retries=args.retries,
                key_rotation_delay=args.key_rotation_delay
            )
            
        elif processing_mode == ProcessingMode.S3_FULL:
            # S3 Full mode - process all S3 images
            logging.error("❌ S3_FULL mode not implemented yet. Use S3_WORKER mode.")
            sys.exit(1)
            
        else:
            # Local mode (default)
            if args.fix:
                logging.error("❌ Fix mode not implemented for S3. Use local mode.")
                sys.exit(1)
            else:
                process_local_mode(
                    max_workers=args.max_workers,
                    retry_errors=not args.no_retry_errors,
                    max_retries=args.retries,
                    key_rotation_delay=args.key_rotation_delay
                )

        if not shutdown_requested:
            if processing_mode == ProcessingMode.S3_WORKER:
                print(f"🎉 S3 Worker processing complete. Results uploaded to S3 bucket.")
            else:
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
