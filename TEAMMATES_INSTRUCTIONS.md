# 🚀 Teammate Processing Instructions

## Overview
You've been assigned a portion of **181,381 remaining images** to process with Vietnamese captions using Google Gemini 2.5 Flash API. Your work will be automatically uploaded to the shared S3 bucket.

## 📋 Prerequisites
- Python 3.8+
- AWS credentials (provided separately)
- Google Gemini API keys (already in the code)

---

## 🛠️ Setup Instructions

### 1. Get the Project
```bash
# Clone or copy the project folder
cd gemini-captioner
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
Copy the environment template and add your credentials:
```bash
cp .env.sample your_config_file
```

Edit your config file with assigned settings and AWS credentials.

---

## 🎯 Choose Your Worker Assignment

### Available Worker Files:
- `work_distribution_remaining/worker_1_images.txt` - **45,346 images**
- `work_distribution_remaining/worker_2_images.txt` - **45,345 images**
- `work_distribution_remaining/worker_3_images.txt` - **45,345 images**
- `work_distribution_remaining/worker_4_images.txt` - **45,345 images**

### Claim Your Assignment:
1. **Pick a worker number** (1-4) and coordinate with team
2. **Configure your worker settings** 
3. **Confirm your assignment** by checking the file:
   ```bash
   head work_distribution_remaining/worker_X_images.txt
   ```

---

## ▶️ Start Processing

### Basic Command:
```bash
# Activate virtual environment first
source venv/bin/activate

# Start processing with worker file
python main.py --processing-mode s3_worker --worker-file work_distribution_remaining/worker_1_images.txt --worker-id worker_1
```

### Advanced Options:
```bash
# Adjust worker threads (default: 10)
python main.py --processing-mode s3_worker --worker-file worker_1_images.txt --max_workers 20

# Increase retries for unstable connections
python main.py --processing-mode s3_worker --worker-file worker_1_images.txt --retries 50

# Show API key usage statistics
python main.py --show-key-stats
```

---

## 📊 Monitoring Progress

### Check Progress:
- The system creates a `checkpoint.pkl` file to track your progress
- **Safe to stop/restart** - it will resume where you left off
- Logs show processing speed and errors

### Sample Output:
```
🚀 Starting processing with 2 Gemini API keys
📂 Loaded checkpoint with 1250 processed files.
🔍 Worker Mode: Processing 45346 images from worker_1_images.txt
📊 Processing: 45346 images to process
🔄 Progress: 100%|██████████| 45346/45346 [2:15:30<00:00, 5.58it/s]
✅ Processing completed successfully!
```

---

## 🔄 Resume After Interruption

If you need to stop and restart:
```bash
# Just run the same command again
python main.py --processing-mode s3_worker --worker-file worker_X_images.txt

# The system automatically:
# ✅ Loads your previous progress
# ✅ Skips already processed images
# ✅ Continues from where you stopped
```

---

## 📁 Output Location

Your processed captions are automatically uploaded to:
- **S3 Bucket**: `aic-2025-bucket`
- **Folder**: `captions/`
- **Format**: `captions/K01/V001/00000123.txt` (matches image structure)

---

## 🔧 Quick Reference Commands

```bash
# Worker 1
python main.py --processing-mode s3_worker --worker-file work_distribution_remaining/worker_1_images.txt --worker-id worker_1

# Worker 2  
python main.py --processing-mode s3_worker --worker-file work_distribution_remaining/worker_2_images.txt --worker-id worker_2

# Worker 3
python main.py --processing-mode s3_worker --worker-file work_distribution_remaining/worker_3_images.txt --worker-id worker_3

# Worker 4
python main.py --processing-mode s3_worker --worker-file work_distribution_remaining/worker_4_images.txt --worker-id worker_4
```
