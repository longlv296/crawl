import os
import time
import requests
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

# Cấu hình API
API_KEY = "sk-IW2l69a10f00269cb14464"
BASE_URL = "https://perenual.com/api/v2/species-list"
BASE_FOLDER = "data" # Thư mục gốc để lưu ảnh

def download_image(img_url):
    """Hàm xử lý việc tải và lưu ảnh vào đúng thư mục"""
    if not img_url:
        return
        
    try:
        # 1. Bóc tách URL để lấy đường dẫn
        parsed_url = urlparse(img_url)
        file_path = parsed_url.path.lstrip('/') # VD: perenual/species_image/.../anh.jpg
        
        # 2. Ghép thêm thư mục gốc "data/" vào trước
        full_path = os.path.join(BASE_FOLDER, file_path)
        
        # 3. Tạo cây thư mục nếu chưa có
        dir_name = os.path.dirname(full_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
            
        # 4. Kiểm tra xem file đã tải chưa để tránh tải lại
        if os.path.exists(full_path):
            print(f"⏩ Bỏ qua (đã tồn tại): {full_path}")
            return

        # 5. Tiến hành tải ảnh
        print(f"⬇️ Đang tải: {full_path}")
        response = requests.get(img_url, stream=True, timeout=15)
        
        if response.status_code == 200:
            with open(full_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
        else:
            print(f"❌ Lỗi tải ảnh. HTTP: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Lỗi trong quá trình tải {img_url}: {e}")

def main():
    print("=== TOOL CRAWL ẢNH PERENUAL API ===")
    
    # Nhập trang bắt đầu và kết thúc
    try:
        start_page = int(input("Nhập trang bắt đầu (VD: 1): "))
        end_page = int(input("Nhập trang kết thúc (VD: 5): "))
    except ValueError:
        print("Vui lòng nhập số nguyên hợp lệ!")
        return

    # Lặp qua từng trang
    for page in range(start_page, end_page + 1):
        print(f"\n--- Đang xử lý dữ liệu Trang {page} ---")
        api_url = f"{BASE_URL}?key={API_KEY}&page={page}"
        
        try:
            # Gọi API lấy dữ liệu JSON
            response = requests.get(api_url, timeout=15)
            
            if response.status_code == 200:
                json_data = response.json()
                plants = json_data.get('data', [])
                
                if not plants:
                    print(f"Trang {page} không có dữ liệu. Chuyển trang tiếp theo.")
                    continue
                
                # Duyệt qua từng cây trong trang để gom toàn bộ link ảnh trước
                urls_to_download = []
                for plant in plants:
                    default_image = plant.get('default_image')
                    
                    # Kiểm tra xem cây có ảnh không (đôi khi API trả về null)
                    if default_image and isinstance(default_image, dict):
                        # Chọn loại ảnh muốn tải (có thể thay bằng 'original_url' nếu muốn ảnh gốc)
                        img_url = default_image.get('regular_url') 
                        if img_url:
                            urls_to_download.append(img_url)

                if urls_to_download:
                    print(f"🚀 Bắt đầu tải {len(urls_to_download)} ảnh của trang {page} bằng luồng đa nhiệm...")
                    # Dùng ThreadPoolExecutor với max_workers (ví dụ: 10 luồng tải song song)
                    # Giúp các ảnh trong cùng 1 trang được tải về bất đồng bộ, nhanh hơn nhiều
                    with ThreadPoolExecutor(max_workers=10) as executor:
                        futures = {executor.submit(download_image, url): url for url in urls_to_download}
                        for future in as_completed(futures):
                            try:
                                future.result()
                            except Exception as exc:
                                print(f"❌ Lỗi trả về từ luồng tải ảnh: {exc}")

            else:
                print(f"❌ Lỗi gọi API trang {page}. HTTP: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Lỗi kết nối ở trang {page}: {e}")
            
        # Nghỉ 2s trước khi qua trang mới để bảo vệ tài khoản API
        print(f"⏳ Nghỉ 2 giây trước khi sang trang {page + 1}...")
        time.sleep(2)
        
    print("\n✅ HOÀN THÀNH QUÁ TRÌNH CRAWL ẢNH!")

if __name__ == "__main__":
    main()
#page 88