#!/usr/bin/env python3
"""
Quick work distribution - skip S3 caption checking since we have checkpoint
"""

import pickle
import os
import logging
from dotenv import load_dotenv
from src.s3_client import S3Client

logging.basicConfig(level=logging.INFO)

def main():
    workers = 4
    
    # Load what coworker already processed
    with open('checkpoint.pkl', 'rb') as f:
        processed_files = pickle.load(f)
    
    # Convert to S3 key format
    processed_s3_keys = {f"frames/{file_path}" for file_path in processed_files}
    
    # Get all S3 images (we already know this list)
    s3_client = S3Client()
    all_images = s3_client.list_all_images()
    
    # Simple subtraction - no S3 API calls needed!
    remaining_images = [img for img in all_images if img not in processed_s3_keys]
    
    print(f"✅ Quick Analysis:")
    print(f"   Total images: {len(all_images)}")
    print(f"   Processed: {len(processed_files)}")
    print(f"   Remaining: {len(remaining_images)}")
    
    # Generate distribution
    chunk_size = len(remaining_images) // workers
    remainder = len(remaining_images) % workers
    
    os.makedirs("work_distribution_remaining", exist_ok=True)
    
    start_idx = 0
    for i in range(workers):
        current_chunk_size = chunk_size + (1 if i < remainder else 0)
        end_idx = start_idx + current_chunk_size
        chunk = remaining_images[start_idx:end_idx]
        
        filename = f"work_distribution_remaining/worker_{i+1}_images.txt"
        with open(filename, 'w') as f:
            f.write(f"# Worker {i+1} - {len(chunk)} images\n")
            f.write(f"# S3 Bucket: aic-2025-bucket\n\n")
            for img in chunk:
                f.write(f"{img}\n")
        
        print(f"   Worker {i+1}: {len(chunk)} images -> {filename}")
        start_idx = end_idx
    
    print(f"\n🎉 Distribution complete in seconds, not hours!")

if __name__ == "__main__":
    main()
