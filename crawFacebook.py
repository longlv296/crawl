import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, parse_qs

# ======================== CẤU HÌNH ========================
BASE_FOLDER = "data_facebook"  # Thư mục gốc để lưu ảnh

# Thông tin đăng nhập Facebook (⚠️ KHÔNG chia sẻ file này lên mạng!)
FB_EMAIL = ""        # Điền email/SĐT Facebook của bạn
FB_PASSWORD = ""     # Điền mật khẩu Facebook của bạn

# URL album hoặc trang Facebook cần crawl ảnh
# Ví dụ:
#   - Album:  https://www.facebook.com/media/set/?set=a.123456789
#   - Photos of page: https://www.facebook.com/TenPage/photos
FB_TARGET_URL = ""   # Điền URL album/page cần crawl

# Số lần cuộn trang để tải thêm ảnh (Facebook dùng lazy loading)
MAX_SCROLL_TIMES = 50

# Số luồng tải ảnh song song
MAX_WORKERS = 10
# ==========================================================


def setup_driver():
    """Khởi tạo trình duyệt Chrome với Selenium"""
    chrome_options = Options()
    # Bỏ comment dòng dưới nếu muốn chạy ẩn trình duyệt (headless)
    # chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-notifications")  # Tắt thông báo
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--lang=vi")
    chrome_options.add_argument("--window-size=1920,1080")
    # Giảm phát hiện bot
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)
    return driver


def login_facebook(driver):
    """Đăng nhập vào Facebook"""
    print("🔐 Đang đăng nhập Facebook...")
    driver.get("https://www.facebook.com/")
    time.sleep(3)

    # Tìm ô nhập email và password
    try:
        email_input = driver.find_element(By.ID, "email")
        pass_input = driver.find_element(By.ID, "pass")

        email_input.clear()
        email_input.send_keys(FB_EMAIL)
        time.sleep(0.5)

        pass_input.clear()
        pass_input.send_keys(FB_PASSWORD)
        time.sleep(0.5)

        pass_input.send_keys(Keys.RETURN)
        time.sleep(5)

        # Kiểm tra đăng nhập thành công
        if "login" in driver.current_url.lower() or "checkpoint" in driver.current_url.lower():
            print("❌ Đăng nhập thất bại! Kiểm tra lại email/mật khẩu.")
            print("   Hoặc Facebook yêu cầu xác minh bảo mật (checkpoint).")
            return False

        print("✅ Đăng nhập thành công!")
        return True

    except Exception as e:
        print(f"❌ Lỗi khi đăng nhập: {e}")
        return False


def scroll_to_load_images(driver, max_scrolls):
    """Cuộn trang để Facebook tải thêm ảnh (lazy loading)"""
    print(f"📜 Đang cuộn trang để tải ảnh (tối đa {max_scrolls} lần)...")
    last_height = driver.execute_script("return document.body.scrollHeight")

    for i in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Đợi ảnh load

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            print(f"   → Đã cuộn hết trang sau {i + 1} lần cuộn.")
            break
        last_height = new_height
        if (i + 1) % 10 == 0:
            print(f"   → Đã cuộn {i + 1}/{max_scrolls} lần...")

    print("✅ Hoàn tất cuộn trang.")


def extract_image_urls(driver):
    """Trích xuất URL ảnh chất lượng cao từ trang hiện tại"""
    print("🔍 Đang tìm kiếm ảnh trên trang...")

    image_urls = set()

    # Cách 1: Tìm thẻ <img> có src chứa ảnh Facebook
    img_elements = driver.find_elements(By.TAG_NAME, "img")
    for img in img_elements:
        src = img.get_attribute("src") or ""
        # Lọc ảnh có kích thước lớn (ảnh bài đăng, album)
        # Facebook thường dùng scontent-*.xx.fbcdn.net cho ảnh
        if "scontent" in src and "fbcdn.net" in src:
            # Ưu tiên ảnh có kích thước lớn
            width = img.get_attribute("width")
            height = img.get_attribute("height")
            natural_width = img.get_attribute("naturalWidth")

            # Bỏ qua ảnh quá nhỏ (icon, avatar nhỏ...)
            try:
                if natural_width and int(natural_width) < 200:
                    continue
            except (ValueError, TypeError):
                pass

            image_urls.add(src)

    # Cách 2: Tìm trong các link dẫn tới ảnh gốc (data-src, srcset)
    for img in img_elements:
        data_src = img.get_attribute("data-src") or ""
        if "scontent" in data_src and "fbcdn.net" in data_src:
            image_urls.add(data_src)

    # Cách 3: Tìm ảnh trong background-image CSS
    divs_with_bg = driver.find_elements(By.CSS_SELECTOR, "[style*='background-image']")
    for div in divs_with_bg:
        style = div.get_attribute("style") or ""
        if "scontent" in style and "fbcdn.net" in style:
            # Trích xuất URL từ background-image: url(...)
            start = style.find("url(") + 4
            end = style.find(")", start)
            if start > 3 and end > start:
                bg_url = style[start:end].strip('"').strip("'")
                image_urls.add(bg_url)

    print(f"✅ Tìm thấy {len(image_urls)} ảnh!")
    return list(image_urls)


def download_image(img_url, index, total):
    """Tải ảnh về thư mục đích"""
    if not img_url:
        return

    try:
        # Tạo tên file dựa trên URL
        parsed = urlparse(img_url)
        filename = os.path.basename(parsed.path)

        # Nếu tên file không có đuôi ảnh, thêm .jpg
        if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            filename = f"fb_image_{index:04d}.jpg"

        # Đường dẫn lưu file
        full_path = os.path.join(BASE_FOLDER, filename)

        # Tránh trùng tên file
        if os.path.exists(full_path):
            name, ext = os.path.splitext(filename)
            full_path = os.path.join(BASE_FOLDER, f"{name}_{index}{ext}")

        # Kiểm tra lại sau khi đổi tên
        if os.path.exists(full_path):
            print(f"⏩ [{index}/{total}] Bỏ qua (đã tồn tại): {full_path}")
            return

        # Tải ảnh
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(img_url, headers=headers, stream=True, timeout=30)

        if response.status_code == 200:
            with open(full_path, 'wb') as f:
                for chunk in response.iter_content(8192):
                    f.write(chunk)
            print(f"✅ [{index}/{total}] Đã tải: {full_path}")
        else:
            print(f"❌ [{index}/{total}] Lỗi HTTP {response.status_code}: {img_url[:80]}...")

    except Exception as e:
        print(f"❌ [{index}/{total}] Lỗi tải ảnh: {e}")


def crawl_full_size_images(driver, image_urls):
    """
    Mở từng ảnh để lấy URL chất lượng cao nhất.
    Facebook thường hiển thị thumbnail nhỏ, cần click vào ảnh để lấy ảnh gốc.
    """
    print("\n🔎 Đang thu thập ảnh chất lượng cao (mở từng ảnh)...")
    high_res_urls = set()

    # Tìm tất cả link dẫn tới ảnh (thẻ <a> chứa /photo/)
    photo_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/photo/"], a[href*="/photos/"]')
    print(f"   → Tìm thấy {len(photo_links)} link ảnh để mở...")

    for i, link in enumerate(photo_links):
        try:
            href = link.get_attribute("href")
            if not href:
                continue

            # Mở ảnh trong tab mới
            driver.execute_script("window.open(arguments[0]);", href)
            driver.switch_to.window(driver.window_handles[-1])
            time.sleep(2)

            # Tìm ảnh lớn nhất trên trang chi tiết
            imgs = driver.find_elements(By.TAG_NAME, "img")
            for img in imgs:
                src = img.get_attribute("src") or ""
                if "scontent" in src and "fbcdn.net" in src:
                    try:
                        nw = int(img.get_attribute("naturalWidth") or 0)
                        if nw > 500:  # Chỉ lấy ảnh lớn
                            high_res_urls.add(src)
                    except (ValueError, TypeError):
                        pass

            # Đóng tab và quay lại tab chính
            driver.close()
            driver.switch_to.window(driver.window_handles[0])

            if (i + 1) % 5 == 0:
                print(f"   → Đã xử lý {i + 1}/{len(photo_links)} ảnh...")

        except Exception as e:
            # Đảm bảo quay lại tab chính nếu lỗi
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
            continue

    if high_res_urls:
        print(f"✅ Thu thập được {len(high_res_urls)} ảnh chất lượng cao!")
        return list(high_res_urls)
    else:
        print("⚠️ Không tìm thêm ảnh HD. Sử dụng danh sách ảnh ban đầu.")
        return image_urls


def main():
    print("=" * 50)
    print("   🖼️  TOOL CRAWL ẢNH FACEBOOK")
    print("=" * 50)

    # Kiểm tra cấu hình
    if not FB_EMAIL or not FB_PASSWORD:
        print("❌ Chưa điền thông tin đăng nhập! Mở file và điền FB_EMAIL, FB_PASSWORD.")
        return

    if not FB_TARGET_URL:
        print("❌ Chưa điền URL album/page cần crawl! Mở file và điền FB_TARGET_URL.")
        return

    # Tạo thư mục lưu ảnh
    os.makedirs(BASE_FOLDER, exist_ok=True)

    # Hỏi người dùng có muốn lấy ảnh HD không
    print("\nChế độ crawl:")
    print("  1. Nhanh - Lấy ảnh thumbnail từ trang (nhanh, chất lượng trung bình)")
    print("  2. HD    - Mở từng ảnh để lấy chất lượng cao nhất (chậm hơn)")
    mode = input("Chọn chế độ (1 hoặc 2, mặc định 1): ").strip()
    hd_mode = mode == "2"

    driver = None
    try:
        # 1. Khởi tạo trình duyệt
        driver = setup_driver()

        # 2. Đăng nhập Facebook
        if not login_facebook(driver):
            return

        # 3. Truy cập trang đích
        print(f"\n🌐 Đang truy cập: {FB_TARGET_URL}")
        driver.get(FB_TARGET_URL)
        time.sleep(5)

        # 4. Cuộn trang để tải thêm ảnh
        scroll_to_load_images(driver, MAX_SCROLL_TIMES)

        # 5. Trích xuất URL ảnh
        image_urls = extract_image_urls(driver)

        if not image_urls:
            print("❌ Không tìm thấy ảnh nào trên trang!")
            return

        # 6. (Tùy chọn) Lấy ảnh chất lượng cao
        if hd_mode:
            image_urls = crawl_full_size_images(driver, image_urls)

        # 7. Tải ảnh về bằng đa luồng
        total = len(image_urls)
        print(f"\n🚀 Bắt đầu tải {total} ảnh bằng {MAX_WORKERS} luồng song song...")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(download_image, url, idx + 1, total): url
                for idx, url in enumerate(image_urls)
            }
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as exc:
                    print(f"❌ Lỗi từ luồng tải: {exc}")

    except Exception as e:
        print(f"❌ Lỗi không mong muốn: {e}")

    finally:
        # 8. Đóng trình duyệt
        if driver:
            driver.quit()
            print("\n🔒 Đã đóng trình duyệt.")

    print(f"\n{'=' * 50}")
    print(f"   ✅ HOÀN THÀNH! Ảnh được lưu tại: {os.path.abspath(BASE_FOLDER)}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
