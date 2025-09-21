#!/usr/bin/env python3
"""
S3 Scanner Script - Inventory all image files and generate work distribution
"""

import sys
import logging
import argparse
from dotenv import load_dotenv

from src.s3_client import S3Client

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    parser = argparse.ArgumentParser(description="Scan S3 bucket and generate work distribution")
    parser.add_argument("--num-workers", type=int, default=4, help="Number of workers for distribution (default: 4)")
    parser.add_argument("--dry-run", action="store_true", help="Only scan, don't generate distribution files")
    parser.add_argument("--output-dir", default="./work_distribution", help="Output directory for distribution files")
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    try:
        # Initialize S3 client
        logging.info("Initializing S3 client...")
        s3_client = S3Client()
        
        # Scan all images
        logging.info("Scanning S3 bucket for all image files...")
        all_images = s3_client.list_all_images()
        
        if not all_images:
            logging.warning("No image files found in S3 bucket!")
            sys.exit(1)
        
        # Print summary
        print(f"\n📊 S3 Bucket Inventory Summary:")
        print(f"   Bucket: {s3_client.bucket_name}")
        print(f"   Region: {s3_client.region}")
        print(f"   Images Folder: {s3_client.images_folder}/")
        print(f"   Total Images: {len(all_images)}")
        
        # Show sample files
        print(f"\n📁 Sample image files:")
        for i, img in enumerate(all_images[:10]):
            print(f"   {i+1:2d}. {img}")
        if len(all_images) > 10:
            print(f"   ... and {len(all_images) - 10} more files")
        
        if args.dry_run:
            print(f"\n🔍 Dry run complete. Use --num-workers to generate distribution files.")
            return
        
        # Generate work distribution
        logging.info(f"Generating work distribution for {args.num_workers} workers...")
        work_chunks = s3_client.generate_work_distribution(all_images, args.num_workers)
        
        # Save distribution files
        distribution_files = s3_client.save_work_distribution_files(work_chunks, args.output_dir)
        
        print(f"\n✅ Work Distribution Generated:")
        print(f"   Output Directory: {args.output_dir}")
        print(f"   Number of Workers: {len(work_chunks)}")
        
        for i, chunk in enumerate(work_chunks):
            if chunk:
                print(f"   Worker {i+1}: {len(chunk)} images")
        
        print(f"\n📝 Distribution Files Created:")
        for file_path in distribution_files:
            print(f"   {file_path}")
        
        print(f"\n🚀 Next Steps:")
        print(f"   1. Set AWS credentials in .env file")
        print(f"   2. Share worker files with teammates")
        print(f"   3. Each worker processes their assigned images")
        print(f"   4. Results are uploaded to: {s3_client.captions_folder}/")
        
    except Exception as e:
        logging.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
