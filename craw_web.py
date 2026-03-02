import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def crawl_perenual_by_id(plant_id):
    """
    Crawl thông tin và hình ảnh từ trang chi tiết của Perenual dựa trên ID.
    """
    url = f"https://perenual.com/plant-species-database-search-finder/species/{plant_id}"
    
    # Header giả lập trình duyệt để tránh bị block
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    }
    
    print(f"Đang truy cập: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() # Báo lỗi nếu HTTP code khác 200
    except requests.exceptions.RequestException as e:
        print(f"❌ Lỗi khi tải trang web (ID: {plant_id}): {e}")
        return

    # Phân tích HTML bằng BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # --- 1. LẤY TÊN CÂY ---
    # Tìm thẻ h1 với class cụ thể
    h1_tag = soup.find('h1', class_='text-5xl font-bold')
    if not h1_tag:
        # Fallback thử tìm h1 đầu tiên nếu class bị đổi
        h1_tag = soup.find('h1')
        
    if not h1_tag:
        print(f"❌ Không tìm thấy tên cây cho ID: {plant_id}. Có thể trang web đã thay đổi cấu trúc.")
        return
        
    raw_ten = h1_tag.text.strip()
    # Format tên: in thường, thay khoảng trắng thành gạch dưới
    formatted_ten = raw_ten.lower().replace(' ', '_').replace('-', '_').replace("'", "")
    
    print(f"✅ Tên cây: {raw_ten} -> Format: {formatted_ten}")
    
    # --- 2. LẤY LINK ẢNH ---
    img_url = None
    # Cách 1: Tìm tất cả các thẻ img, lọc thẻ img có `src` bắt đầu bằng `https://s3.us-central-1.wasabisys.com/perenual/species_image/`
    img_tags = soup.find_all('img')
    for img in img_tags:
        src = img.get('src')
        # Kiểm tra xem link có giống định dạng link ảnh AWS S3 của perenual không
        if src and "s3.us-central-1.wasabisys.com/perenual/species_image" in src:
            img_url = src
            # Lấy ảnh đầu tiên tìm thấy là ảnh đại diện
            break
            
    if not img_url:
        print(f"⚠️ Không tìm thấy link ảnh cho cây: {raw_ten}")
        return
        
    print(f"✅ Found Image URL: {img_url.split('?')[0]}...")
    
    # --- 3. LƯU ẢNH ---
    parsed_url = urlparse(img_url)
    path_parts = parsed_url.path.strip('/').split('/')
    
    # Lấy đường dẫn thư mục từ URL (bỏ tên file cuối cùng)
    if len(path_parts) > 1:
        relative_dir = os.path.join(*path_parts[:-1])
    else:
        folder_name = f"{plant_id}_{formatted_ten}"
        relative_dir = os.path.join("perenual", "species_image", folder_name, "regular")
        
    save_dir = os.path.join("data", relative_dir)
    
    # Tạo thư mục nếu chưa tồn tại
    os.makedirs(save_dir, exist_ok=True)
    
    # Đường dẫn file ảnh
    save_path = os.path.join(save_dir, "image.jpg")
    
    # Bỏ qua nếu đã tải rồi
    if os.path.exists(save_path):
        print(f"⏩ Ảnh đã tồn tại: {save_path}")
        return
        
    # Tiến hành tải ảnh
    print(f"⬇️ Đang tải ảnh về: {save_path}")
    try:
        img_response = requests.get(img_url, headers=headers, stream=True, timeout=15)
        img_response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in img_response.iter_content(1024):
                f.write(chunk)
                
        print(f"✅ Đã tải thành công ảnh: {save_path}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Lỗi khi tải ảnh cho cây {raw_ten}: {e}")

from concurrent.futures import ThreadPoolExecutor, as_completed

def main():
    print("=== TOOL CRAWL PERENUAL BẰNG ID TỪ WEB (ĐA LUỒNG) ===")
    
    try:
        start_id = int(input("Nhập ID bắt đầu (VD: 3000): "))
        end_id = int(input("Nhập ID kết thúc (VD: 3050): "))
    except ValueError:
        print("⚠️ Lỗi: Vui lòng chỉ nhập số nguyên!")
        return
        
    if start_id > end_id:
        print("⚠️ ID bắt đầu phải nhỏ hơn hoặc bằng ID kết thúc.")
        return
        
    # Tạo danh sách ID từ start_id đến end_id
    valid_ids = list(range(start_id, end_id + 1))
    
    print(f"🚀 Bắt đầu crawl dữ liệu cho {len(valid_ids)} ID từ {start_id} đến {end_id}...")
    print("-" * 50)
    
    # Tối ưu thời gian bằng cách dùng multi-threading
    # max_workers=10 nghĩa là tải tối đa 10 ID cùng lúc
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Gửi tất cả các tác vụ crawl vào thread pool
        futures = {executor.submit(crawl_perenual_by_id, str(pid)): pid for pid in valid_ids}
        
        # as_completed giúp xử lý ngay khi một luồng hoàn thành thay vì phải chờ tất cả
        for future in as_completed(futures):
            pid = futures[future]
            try:
                future.result()
            except Exception as exc:
                print(f"❌ ID {pid} xảy ra lỗi: {exc}")
                
    print("\n✅ HOÀN TẤT QUÁ TRÌNH CRAWL!")

if __name__ == "__main__":
    main()
