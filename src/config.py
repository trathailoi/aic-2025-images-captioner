"""
Configuration module for Gemini Image Captioner.
Contains all constants, API keys, and configuration settings.
"""

import os
import argparse
from typing import Optional
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Configure multiple GenAI API keys for rotation
GENAI_API_KEYS = [
    # 'AIzaSyCrrYXkgA5qfwyZkcA0QIbc4E6xNUdDr2A',
    # 'AIzaSyApaw7U5O9VpepbbHOxwKwYJIf2-0KmwEs',
    'AIzaSyCVXSEeslcOMbR-g-q4_8JvndaTcLwZe5M',
    'AIzaSyAgrxrTAjyGf9s2HIuAWH1aDmTxBD-Y2Vg'
]

# ==============================================================================
# PROCESSING MODE CONFIGURATION
# ==============================================================================

# Processing modes
class ProcessingMode:
    LOCAL = "local"          # Process local directory
    S3_FULL = "s3_full"      # Process all S3 images
    S3_WORKER = "s3_worker"  # Process assigned worker list

# Get processing mode from environment
PROCESSING_MODE = os.getenv('PROCESSING_MODE', ProcessingMode.LOCAL)

# ==============================================================================
# LOCAL MODE CONFIGURATION (Original)
# ==============================================================================

# Local directory paths (for backward compatibility)
INPUT_DIR = "/Volumes/Bobbie/AIO2025/scr/S3/images"
OUTPUT_DIR = "/Volumes/Bobbie/AIO2025/scr/S3/captions"

# ==============================================================================
# S3 CONFIGURATION
# ==============================================================================

# S3 settings from environment variables
AWS_REGION = os.getenv('AWS_REGION', 'ap-southeast-1')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'aic-2025-bucket')
S3_IMAGES_FOLDER = os.getenv('S3_IMAGES_FOLDER', 'frames')
S3_CAPTIONS_FOLDER = os.getenv('S3_CAPTIONS_FOLDER', 'captions')

# ==============================================================================
# WORKER ASSIGNMENT CONFIGURATION
# ==============================================================================

# Worker file path - contains list of images to process
WORKER_FILE_PATH = os.getenv('WORKER_FILE_PATH', None)

# Worker ID for logging/identification
WORKER_ID = os.getenv('WORKER_ID', 'default')

# ==============================================================================
# ERROR DETECTION AND RATE LIMITING
# ==============================================================================

# Error detection patterns
ERROR_MESSAGES = [
    "An internal error has occurred. Please retry or report in https://developers.generativeai.google/guide/troubleshooting",
    "Error in process_and_save for",
    "500 An internal error has occurred",
    "500 INTERNAL",
    "503 Service Unavailable",
    "Server is overloaded",
    "Error processing",
    "error",  # Generic error detection
    "Max retries",  # When our retry logic gives up
    "Error processing with Gemini",
    "RESOURCE_EXHAUSTED.",
    "The model is overloaded."
]

RATE_LIMIT_MESSAGES = [
    "Error code: 429",  # Rate limiting
    "insufficient_quota",  # Quota exceeded
    "exceeded your current quota",  # Quota message
    "Rate limit exceeded",  # Rate limiting variations
    "Too many requests",
    "RESOURCE_EXHAUSTED",
    "Quota exceeded",
    "quota_exceeded",
    "rate_limit_exceeded"
]

# Configure maximum relaxed safety settings
SAFETY_SETTINGS = [
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
]

# Supported image file extensions
IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.bmp')

# Default configuration values
DEFAULT_MAX_WORKERS = 10
DEFAULT_MAX_RETRIES = 30
DEFAULT_KEY_ROTATION_DELAY = 1.0
DEFAULT_RATE_LIMIT_CALLS = 1000
DEFAULT_RATE_LIMIT_PERIOD = 60

# Define the updated prompt
PROMPT = """
**Nhiệm vụ**: Phân tích hình ảnh và cung cấp metadata có cấu trúc cùng mô tả tự nhiên chi tiết bằng tiếng Việt.

### Hướng dẫn:
1. **Metadata có cấu trúc**: Thu thập thông tin theo thứ tự đã định
2. **Chỉ bao gồm đối tượng có thật**: Không tạo trường cho đối tượng không tồn tại trong cảnh
3. **Đặt tên đối tượng cụ thể**: Sử dụng tên riêng biệt, có thể tìm kiếm được (ví dụ: "boats", "bicycles", "flowers", "signs" thay vì "man_made_objects", "decorations")
4. **Scene_text linh hoạt**: Tự do tạo nhóm văn bản phù hợp nếu phát hiện chữ viết trong cảnh
5. **Đếm chính xác**: Chỉ sử dụng số nguyên dương (1, 2, 3...), nếu quá nhiều để đếm thì ước lượng số lượng hoặc ghi "nhiều" trong description
6. **Sử dụng "None"**: Cho bất kỳ trường nào không thể xác định hoặc không tồn tại trong cảnh
7. **Loại trừ đồ họa tin tức khỏi caption**: Không đề cập logo kênh, ticker, đồng hồ trong caption cuối
8. **Caption chỉ góc quay đặc biệt**: Chỉ đề cập góc quay trong caption nếu thực sự đặc biệt ("từ trên cao", "cận cảnh", "từ camera hành trình", vv), bỏ qua các góc thông thường ("ngang mắt", "trung bình", "tĩnh", vv)

### Format JSON:
{
  "camera": {
    "angle": "", // Góc quay: "từ trên cao", "mặt đất", "góc thấp", "góc cao", "ngang mắt", vv
    "shot_type": "", // Loại shot: "cận cảnh", "trung bình", "toàn cảnh", "cực rộng", vv
    "movement": "" // Chuyển động camera: "tĩnh", "quay ngang", "zoom", "rung lắc", "theo dõi", vv
  },
  "setting": {
    "location": "", // Địa điểm: "sân bóng đá", "lớp học", "trạm xăng", "đường phố", vv
    "environment": "", // Môi trường: "trong nhà", "ngoài trời", "bán kín", vv
    "venue_type": "", // Loại địa điểm: "thể thao", "giáo dục", "thương mại", "công cộng", vv
    "time_of_day": "" // Thời gian: "ban ngày", "buổi tối", "hoàng hôn", "ban đêm", vv
  },
  "objects": {
    // CHỈ bao gồm đối tượng thực sự tồn tại trong cảnh
    // Sử dụng tên cụ thể, có thể tìm kiếm: people, boats, bicycles, flowers, books, signs, buildings, etc.
    "people": {
      "count": 0, // Số lượng người (số nguyên dương)
      "description": "" // Mô tả chi tiết: giới tính, độ tuổi, màu quần áo, phụ kiện, vv
    },
    "vehicles": {
      "count": 0, // Số lượng phương tiện (số nguyên dương)
      "description": "" // Mô tả: loại xe, màu sắc, kích thước, trạng thái, vv
    },
    "animals": {
      "count": 0, // Số lượng động vật (số nguyên dương)
      "description": "" // Mô tả: loại động vật, màu sắc, kích thước, hành động, vv
    }
    // Ba nhóm trên: people, vehicles, animals chỉ là ví dụ mẫu, không bắt buộc phải có
    // Tự do thêm nhóm khác với tên cụ thể: boats, bicycles, flowers, signs, buildings, furniture, sports_equipment, food_items, etc.
    // Mỗi nhóm cần có count (số nguyên dương) và description
  },
  "spatial": {
    "left_side": "", // Mô tả đối tượng/hoạt động ở bên trái khung hình
    "right_side": "", // Mô tả đối tượng/hoạt động ở bên phải khung hình
    "center": "", // Mô tả đối tượng/hoạt động ở giữa khung hình
    "top": "", // Mô tả đối tượng/hoạt động ở phía trên khung hình
    "bottom": "", // Mô tả đối tượng/hoạt động ở phía dưới khung hình
    "foreground": "", // Mô tả đối tượng/hoạt động ở tiền cảnh
    "background": "" // Mô tả đối tượng/hoạt động ở hậu cảnh
  },
  "activity": {
    "primary_action": "", // Hành động chính đang diễn ra
    "secondary_actions": [], // Các hành động phụ khác
    "movement_patterns": "" // Mô tả cách di chuyển: "từ trái sang phải", "tiến về phía trước", vv
  },
  "text_elements": {
    "time_display": "", // Hiển thị thời gian trên màn hình (HH:MM:SS)
    "channel_logo": "", // Logo kênh hoặc nhận dạng đài (CHỈ để phân tích, KHÔNG đưa vào caption)
    "news_ticker": "", // Tin tức cuộn dưới màn hình (CHỈ để phân tích, KHÔNG đưa vào caption)
    "graphics_overlay": "", // Đồ họa, biểu đồ chồng lên cảnh (CHỈ để phân tích, KHÔNG đưa vào caption)
    "scene_text": {
      // Tự do tạo nhóm phù hợp với tên cụ thể: street_signs, billboards, shop_names, chalkboard_writing, building_numbers, etc.
      // Ví dụ:
      // "billboards": [], // Văn bản trên bảng quảng cáo
      // "street_signs": [], // Văn bản trên biển báo đường
      // "numbers": [] // Số hiệu, điểm số hiện trong cảnh thực tế
    }
  },
  "caption": "" // Tổng hợp tất cả thông tin trên thành mô tả tự nhiên, chi tiết, LOẠI TRỪ hoàn toàn đồ họa tin tức
}

### Ví dụ mẫu cho trường "caption":

**Ví dụ 1**: "Cảnh quay từ trên cao một sân bóng đá, hai đội mặc áo trắng và xanh dương, đang thực hiện quả phạt đền, có 4 cầu thủ Uzbekistan trong khung hình."

**Ví dụ 2**: "Cảnh quay cận cảnh một người đàn ông tóc trắng đang cầm cửa kính viền đen, trước mặt có lá cờ nhiều màu đỏ vàng xanh, xung quanh có nhiều micro được đưa lên trong đó có một chiếc micro màu xanh lá."

**Ví dụ 3**: "Cảnh quay một trạm xăng với một người đang đổ xăng cho khách hàng, sau đó có một người bỏ chạy khi một chiếc xe khác lao thẳng vào vị trí đang đổ xăng."

**Ví dụ 4**: "Cảnh trong một lớp học, bảng trang trí trên tường có thể nhìn rõ 5 bông hoa to theo thứ tự màu xanh dương, cam, vàng, xanh lá, đỏ, bên dưới những bông hoa này ghi lớp 1A với một số."

**Ví dụ 5**: "Cảnh một người đang trèo lên cây hái quả sầu riêng, có 1 người mặc áo xanh và 1 người mặc áo đen đứng dưới hỗ trợ."

### Quy tắc đặc biệt cho caption:
- **PHẢI LOẠI TRỪ**: Logo kênh (HTV Online, VTC, etc.), ticker tin tức, đồng hồ hiển thị, đồ họa overlay
- **PHẢI LOẠI TRỪ**: Góc quay thông thường ("ngang mắt", "trung bình", "tĩnh")
- **CHỈ BAO GỒM**: Góc quay đặc biệt ("từ trên cao", "cận cảnh", "góc thấp")
- **CHỈ BAO GỒM**: Nội dung thực của cảnh, đối tượng, màu sắc, số lượng, hành động, vị trí

**Lưu ý quan trọng**:
- Sử dụng "None" cho bất kỳ trường nào không thể xác định
- Trường "caption" phải tổng hợp tất cả metadata thành mô tả tự nhiên như các ví dụ mẫu
- Bao gồm đầy đủ: góc quay (nếu đặc biệt), bối cảnh, đối tượng với số lượng và chi tiết, vị trí không gian, hành động
- TUYỆT ĐỐI không đề cập đến đồ họa tin tức trong caption cuối cùng
"""

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Image Captioning Script with Error Recovery and API Key Rotation")
    parser.add_argument("--fix", action="store_true", help="Run in fix mode to correct error files")
    parser.add_argument("--max_workers", type=int, default=DEFAULT_MAX_WORKERS, help="Maximum number of worker threads")
    parser.add_argument("--no-retry-errors", action="store_true", help="Don't automatically retry error files on startup")
    parser.add_argument("--retries", type=int, default=DEFAULT_MAX_RETRIES, help="Max retries for Gemini API errors (default: 30)")
    parser.add_argument("--key-rotation-delay", type=float, default=DEFAULT_KEY_ROTATION_DELAY, help="Delay in seconds between key rotations (default: 1.0)")
    parser.add_argument("--show-key-stats", action="store_true", help="Show API key statistics and exit")
    
    # New arguments for distributed processing
    parser.add_argument("--worker-file", type=str, help="Path to worker file containing list of images to process")
    parser.add_argument("--worker-id", type=str, default="default", help="Worker ID for identification in logs")
    parser.add_argument("--processing-mode", choices=[ProcessingMode.LOCAL, ProcessingMode.S3_FULL, ProcessingMode.S3_WORKER], 
                       default=ProcessingMode.LOCAL, help="Processing mode: local, s3_full, or s3_worker")
    
    return parser.parse_args()

def get_image_list_from_worker_file(worker_file_path: str) -> list:
    """Load image paths from worker assignment file."""
    images = []
    try:
        with open(worker_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#'):
                    images.append(line)
        return images
    except Exception as e:
        raise Exception(f"Error reading worker file {worker_file_path}: {e}")
