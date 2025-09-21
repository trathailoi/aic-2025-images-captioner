#!/usr/bin/env python3
"""
Generate work distribution for remaining images (non-interactive)
"""

import pickle
import logging
import sys
from dotenv import load_dotenv

from src.s3_client import S3Client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    load_dotenv()
    
    try:
        # Get number of workers from command line
        workers = int(sys.argv[1]) if len(sys.argv) > 1 else 4
        
        # Load checkpoint
        logging.info("Loading checkpoint.pkl...")
        with open('checkpoint.pkl', 'rb') as f:
            processed_files = pickle.load(f)
        
        # Convert local paths to S3 keys format
        processed_s3_keys = set()
        for file_path in processed_files:
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
        
        print(f"\n✅ Work Distribution Summary:")
        print(f"   Total images in S3: {len(all_images)}")
        print(f"   Already processed: {len(processed_files)}")
        print(f"   Remaining to process: {len(remaining_images)}")
        print(f"   Progress: {len(processed_files)/len(all_images)*100:.1f}%")
        
        # Generate work distribution for remaining images
        work_chunks = s3_client.generate_work_distribution(remaining_images, workers)
        distribution_files = s3_client.save_work_distribution_files(work_chunks, "./work_distribution_remaining")
        
        print(f"\n🎯 Generated work distribution for {workers} workers:")
        for i, chunk in enumerate(work_chunks):
            if chunk:
                print(f"   Worker {i+1}: {len(chunk)} images")
        
        print(f"\n📝 Distribution files created:")
        for file_path in distribution_files:
            print(f"   {file_path}")
            
    except Exception as e:
        logging.error(f"Error: {e}")

if __name__ == "__main__":
    main()
