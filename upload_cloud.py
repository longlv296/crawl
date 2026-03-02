import os
import mimetypes
import boto3
from botocore.exceptions import ClientError
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================= CẤU HÌNH CLOUDFLARE R2 =================
ACCOUNT_ID = "8be2d37c330d3bfa71b1514ddcb76e84" # Có thể lấy trong đường link Endpoint
ACCESS_KEY = "92fe5889d95d5e228861981e10d7bc21"
SECRET_KEY = "a56ca4f3b0c2cff6492110ac704208b313454eb61352fb40a7fa8eb7a39874ea"
BUCKET_NAME = "perenualfull" # Tên bucket bạn đã tạo
ENDPOINT_URL = "https://8be2d37c330d3bfa71b1514ddcb76e84.r2.cloudflarestorage.com" # Copy y hệt Endpoint của bạn vào đây

# Thư mục chứa 15GB ảnh trên máy bạn (VD: thư mục 'data' ở bài trước)
LOCAL_FOLDER = "data" 

# ==========================================================

# Khởi tạo kết nối đến R2
s3_client = boto3.client(
    's3',
    endpoint_url=ENDPOINT_URL,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    region_name='auto' # Cloudflare R2 luôn dùng 'auto'
)

def upload_single_file(local_path, s3_key, bucket_name):
    # Xác định loại file (VD: image/jpeg) để trình duyệt không bị lỗi khi xem ảnh
    content_type, _ = mimetypes.guess_type(local_path)
    if content_type is None:
        content_type = 'application/octet-stream'

    try:
        print(f"⬆️ Đang tải lên: {s3_key}")
        
        # Hàm upload file của boto3
        s3_client.upload_file(
            local_path, 
            bucket_name, 
            s3_key,
            ExtraArgs={'ContentType': content_type} # Rất quan trọng để xem ảnh trên web
        )
    except ClientError as e:
        print(f"❌ Lỗi khi tải lên {local_path}: {e}")

def upload_folder_to_r2(local_folder, bucket_name):
    print(f"🚀 Bắt đầu quét thư mục: {local_folder}")
    
    files_to_upload = []
    
    # os.walk giúp duyệt qua toàn bộ thư mục gốc và các thư mục con
    for root, dirs, files in os.walk(local_folder):
        for file in files:
            # Đường dẫn thực tế của file trên máy tính
            local_path = os.path.join(root, file)
            
            # Tạo đường dẫn (Key) trên R2 để giữ nguyên cấu trúc thư mục
            # Dùng replace('\', '/') để đảm bảo format URL chuẩn trên Windows
            s3_key = os.path.relpath(local_path, local_folder).replace('\\', '/')
            
            files_to_upload.append((local_path, s3_key))

    if files_to_upload:
        print(f"📦 Tìm thấy {len(files_to_upload)} file. Bắt đầu tải lên bằng luồng đa nhiệm...")
        
        # Dùng ThreadPoolExecutor để tải đa luồng
        with ThreadPoolExecutor(max_workers=20) as executor:
            # Gửi các task vào pool
            futures = [
                executor.submit(upload_single_file, local_path, s3_key, bucket_name) 
                for local_path, s3_key in files_to_upload
            ]
            
            # Chờ hoàn thành
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as exc:
                    print(f"❌ Có lỗi xảy ra trong một luồng: {exc}")

    print("\n✅ ĐÃ HOÀN TẤT VIỆC TẢI LÊN TOÀN BỘ ẢNH!")

if __name__ == "__main__":
    # Thay ENDPOINT_URL cho đúng cú pháp trước khi chạy
    if "{ACCOUNT_ID}" in ENDPOINT_URL:
        print("Vui lòng thay thế ENDPOINT_URL bằng đường dẫn chính xác của bạn!")
    else:
        upload_folder_to_r2(LOCAL_FOLDER, BUCKET_NAME)