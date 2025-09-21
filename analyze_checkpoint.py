#!/usr/bin/env python3
"""
Analyze checkpoint file and generate remaining work distribution
"""

import pickle
import logging
from dotenv import load_dotenv

from src.s3_client import S3Client

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    load_dotenv()
    
    try:
        # Load checkpoint
        logging.info("Loading checkpoint.pkl...")
        with open('checkpoint.pkl', 'rb') as f:
            processed_files = pickle.load(f)
        
        print(f"📊 Checkpoint Analysis:")
        print(f"   Processed by coworker: {len(processed_files)} images")
        
        # Convert local paths to S3 keys format
        processed_s3_keys = set()
        for file_path in processed_files:
            # Convert K05/V010/00000684.jpg -> frames/K05/V010/00000684.jpg
            s3_key = f"frames/{file_path}"
            processed_s3_keys.add(s3_key)
        
        # Initialize S3 client
        logging.info("Connecting to S3...")
        s3_client = S3Client()
        
        # Get all images from S3
        logging.info("Scanning S3 for all images...")
        all_images = s3_client.list_all_images()
        
        # Find remaining images to process
        remaining_images = []
        for image_key in all_images:
            if image_key not in processed_s3_keys:
                remaining_images.append(image_key)
        
        print(f"\n🎯 Work Distribution Summary:")
        print(f"   Total images in S3: {len(all_images)}")
        print(f"   Already processed: {len(processed_files)}")
        print(f"   Remaining to process: {len(remaining_images)}")
        print(f"   Progress: {len(processed_files)/len(all_images)*100:.1f}%")
        
        # Show some sample remaining files
        print(f"\n📁 Sample remaining files:")
        for i, img in enumerate(remaining_images[:10]):
            print(f"   {i+1:2d}. {img}")
        if len(remaining_images) > 10:
            print(f"   ... and {len(remaining_images) - 10} more files")
        
        # Ask for number of workers
        print(f"\n💡 Suggested distribution:")
        for workers in [2, 3, 4, 6, 8]:
            per_worker = len(remaining_images) // workers
            print(f"   {workers} workers: ~{per_worker:,} images each")
        
        # Generate work distribution for remaining images
        workers = input(f"\nHow many workers do you want to split the remaining {len(remaining_images)} images? (default: 4): ")
        workers = int(workers) if workers.strip() else 4
        
        work_chunks = s3_client.generate_work_distribution(remaining_images, workers)
        distribution_files = s3_client.save_work_distribution_files(work_chunks, "./work_distribution_remaining")
        
        print(f"\n✅ Generated work distribution for remaining images:")
        for file_path in distribution_files:
            print(f"   {file_path}")
            
    except Exception as e:
        logging.error(f"Error: {e}")

if __name__ == "__main__":
    main()
