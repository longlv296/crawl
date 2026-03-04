import os
import csv
import json
import time
import random
import requests
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote_plus

# ======================== CẤU HÌNH ========================
BASE_FOLDER = "data_tiki"              # Thư mục gốc lưu dữ liệu
IMAGE_FOLDER = "data_tiki/images"      # Thư mục lưu ảnh sản phẩm

# Danh sách URL sản phẩm Tiki cần crawl (lấy từ trang chi tiết)
# Ví dụ: https://tiki.vn/ten-san-pham-p12345678.html
PRODUCT_URLS = [
    # Điền URL sản phẩm vào đây, mỗi URL trên 1 dòng
    # "https://tiki.vn/ten-san-pham-p12345678.html",
]

# HOẶC: Crawl từ trang tìm kiếm theo từ khóa
SEARCH_KEYWORDS = [
    # Điền từ khóa tìm kiếm, mỗi từ khóa trên 1 dòng
    # "tai nghe bluetooth",
    # "bàn phím cơ",
    "samsung",
]

# Số trang tìm kiếm tối đa cho mỗi từ khóa (mỗi trang ~40 sản phẩm)
MAX_SEARCH_PAGES = 3

# Có tải ảnh sản phẩm về không?
DOWNLOAD_IMAGES = True

# Số luồng tải ảnh song song
MAX_WORKERS = 5

# API Endpoints
TIKI_SEARCH_API = "https://tiki.vn/api/personalish/v1/blocks/listings"
TIKI_PRODUCT_API = "https://tiki.vn/api/v2/products/{product_id}"
# ==========================================================

# Headers giả lập trình duyệt thật
HEADERS_LIST = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://tiki.vn/",
        "Connection": "keep-alive",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
                      "(KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
        "Referer": "https://tiki.vn/",
        "Connection": "keep-alive",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) "
                      "Gecko/20100101 Firefox/121.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "vi-VN,vi;q=0.5",
        "Referer": "https://tiki.vn/",
        "Connection": "keep-alive",
    },
]


def get_random_headers():
    """Trả về headers ngẫu nhiên để tránh bị phát hiện bot"""
    return random.choice(HEADERS_LIST)


def safe_request(url, params=None, max_retries=3):
    """Gửi request với cơ chế retry và delay ngẫu nhiên"""
    for attempt in range(max_retries):
        try:
            # Delay ngẫu nhiên 2-5 giây giữa các request
            delay = random.uniform(2, 5)
            time.sleep(delay)

            response = requests.get(
                url,
                params=params,
                headers=get_random_headers(),
                timeout=20
            )

            if response.status_code == 200:
                return response
            elif response.status_code == 429:
                # Rate limit - đợi lâu hơn
                print(f"⚠️ Tiki rate limit (429). Đợi 30 giây...")
                time.sleep(30)
            elif response.status_code == 404:
                print(f"❌ Không tìm thấy: {url}")
                return None
            else:
                print(f"⚠️ HTTP {response.status_code} - Thử lại ({attempt + 1}/{max_retries})...")
                time.sleep(10)

        except Exception as e:
            print(f"⚠️ Lỗi kết nối ({attempt + 1}/{max_retries}): {e}")
            time.sleep(5)

    print(f"❌ Không thể truy cập sau {max_retries} lần thử: {url[:80]}...")
    return None


def extract_product_id(url):
    """Trích xuất product ID từ URL Tiki"""
    # Pattern: https://tiki.vn/ten-san-pham-p12345678.html
    match = re.search(r'-p(\d+)\.html', url)
    if match:
        return match.group(1)

    # Pattern: https://tiki.vn/api/v2/products/12345678
    match = re.search(r'/products/(\d+)', url)
    if match:
        return match.group(1)

    return None


def search_tiki(keyword, max_pages=3):
    """Tìm kiếm sản phẩm trên Tiki và trả về danh sách product IDs"""
    print(f"\n🔎 Đang tìm kiếm trên Tiki: '{keyword}' (tối đa {max_pages} trang)...")
    product_ids = []

    for page in range(1, max_pages + 1):
        params = {
            "limit": 40,
            "include": "advertisement",
            "aggregations": 2,
            "version": "home-persionalized",
            "trackity_id": "",
            "category": 0,
            "page": page,
            "q": keyword,
        }

        print(f"   → Trang {page}/{max_pages}...")

        response = safe_request(TIKI_SEARCH_API, params=params)
        if not response:
            continue

        try:
            data = response.json()
            items = data.get("data", [])

            if not items:
                print(f"   → Trang {page}: Không tìm thấy sản phẩm. Dừng tìm kiếm.")
                break

            for item in items:
                pid = item.get("id")
                if pid and pid not in product_ids:
                    product_ids.append(pid)

            print(f"   → Trang {page}: Tìm thấy {len(items)} sản phẩm.")

        except Exception as e:
            print(f"   ⚠️ Lỗi phân tích JSON trang {page}: {e}")

    print(f"✅ Tổng cộng tìm thấy {len(product_ids)} sản phẩm cho '{keyword}'.")
    return product_ids


def scrape_product_detail(product_id):
    """Crawl toàn bộ thông tin chi tiết của 1 sản phẩm từ API"""
    url = TIKI_PRODUCT_API.format(product_id=product_id)
    print(f"\n🔍 Đang crawl sản phẩm ID: {product_id}")

    params = {
        "platform": "web",
        "spid": product_id,
        "version": 3,
    }

    response = safe_request(url, params=params)
    if not response:
        return None

    try:
        data = response.json()
    except Exception as e:
        print(f"❌ Lỗi phân tích JSON: {e}")
        return None

    product = {
        "product_id": str(product_id),
        "url": f"https://tiki.vn/{data.get('url_path', '')}",
        "title": "",
        "price": "",
        "original_price": "",
        "discount": "",
        "discount_rate": "",
        "rating": "",
        "review_count": "",
        "quantity_sold": "",
        "availability": "",
        "brand": "",
        "category": "",
        "description": "",
        "short_description": "",
        "features": [],
        "specifications": {},
        "images": [],
        "thumbnail": "",
        "seller": "",
        "seller_id": "",
        "coupons": [],
        "badges": [],
        "sku": "",
        "inventory_status": "",
    }

    try:
        # --- Tên sản phẩm ---
        product["title"] = data.get("name", "")

        # --- Giá hiện tại ---
        product["price"] = str(data.get("price", ""))

        # --- Giá gốc (trước giảm giá) ---
        original = data.get("original_price") or data.get("list_price", "")
        product["original_price"] = str(original) if original else ""

        # --- Giảm giá ---
        discount_rate = data.get("discount_rate", 0)
        if discount_rate:
            product["discount_rate"] = f"-{discount_rate}%"
            product["discount"] = str(data.get("discount", ""))

        # --- Đánh giá (rating) ---
        rating_avg = data.get("rating_average", 0)
        product["rating"] = str(rating_avg) if rating_avg else ""

        # --- Số lượng review ---
        product["review_count"] = str(data.get("review_count", ""))

        # --- Số lượng đã bán ---
        qty_sold = data.get("all_time_quantity_sold") or data.get("quantity_sold", {})
        if isinstance(qty_sold, dict):
            product["quantity_sold"] = qty_sold.get("text", "")
        else:
            product["quantity_sold"] = str(qty_sold)

        # --- Tình trạng hàng ---
        stock = data.get("stock_item", {})
        if isinstance(stock, dict):
            product["availability"] = "Còn hàng" if stock.get("qty", 0) > 0 else "Hết hàng"
            product["inventory_status"] = str(stock.get("qty", ""))
        else:
            product["availability"] = "Còn hàng" if data.get("inventory_status") == "available" else "Hết hàng"
            product["inventory_status"] = data.get("inventory_status", "")

        # --- Thương hiệu ---
        brand = data.get("brand", {})
        if isinstance(brand, dict):
            product["brand"] = brand.get("name", "")
        else:
            product["brand"] = str(brand) if brand else ""

        # --- Danh mục (breadcrumb) ---
        breadcrumbs = data.get("breadcrumbs", [])
        if breadcrumbs:
            categories = [b.get("name", "") for b in breadcrumbs if b.get("name")]
            product["category"] = " > ".join(categories)

        # --- Mô tả sản phẩm ---
        product["description"] = data.get("description", "")
        product["short_description"] = data.get("short_description", "")

        # --- Tính năng nổi bật ---
        highlights = data.get("highlight", "") or data.get("short_description", "")
        if highlights:
            # Trích xuất text từ HTML nếu cần
            clean_text = re.sub(r'<[^>]+>', '\n', str(highlights))
            features = [f.strip() for f in clean_text.split('\n') if f.strip()]
            product["features"] = features

        # --- Thông số kỹ thuật ---
        specifications = data.get("specifications", [])
        if specifications:
            for spec_group in specifications:
                group_name = spec_group.get("name", "")
                attributes = spec_group.get("attributes", [])
                for attr in attributes:
                    key = attr.get("name", "")
                    value = attr.get("value", "")
                    if key and value:
                        full_key = f"{group_name} - {key}" if group_name else key
                        product["specifications"][full_key] = value

        # --- Ảnh sản phẩm ---
        # Ảnh chính
        thumbnail = data.get("thumbnail_url", "")
        if thumbnail:
            product["thumbnail"] = thumbnail

        # Tất cả ảnh
        images = data.get("images", [])
        if images:
            for img in images:
                if isinstance(img, dict):
                    img_url = img.get("large_url") or img.get("base_url") or img.get("medium_url", "")
                elif isinstance(img, str):
                    img_url = img
                else:
                    continue

                if img_url and img_url not in product["images"]:
                    product["images"].append(img_url)

        # Nếu không có images, thêm thumbnail
        if not product["images"] and thumbnail:
            product["images"].append(thumbnail)

        # --- SKU ---
        product["sku"] = str(data.get("sku", ""))

        # --- Người bán ---
        seller = data.get("current_seller", {})
        if isinstance(seller, dict):
            product["seller"] = seller.get("name", "")
            product["seller_id"] = str(seller.get("id", ""))

        # --- Mã giảm giá / Coupon ---
        coupons = data.get("coupon_hot_label", "") or data.get("coupon_tag_info", {})
        if isinstance(coupons, dict):
            coupon_text = coupons.get("text", "")
            if coupon_text:
                product["coupons"].append(coupon_text)
        elif isinstance(coupons, str) and coupons:
            product["coupons"].append(coupons)

        # Thêm freeship badge, installment, v.v.
        badges_new = data.get("badges_new", [])
        if badges_new:
            for badge in badges_new:
                if isinstance(badge, dict):
                    badge_text = badge.get("text", "") or badge.get("icon", "")
                    if badge_text:
                        product["badges"].append(badge_text)

        print(f"✅ Đã crawl: {product['title'][:60] if product['title'] else 'N/A'}...")

    except Exception as e:
        print(f"❌ Lỗi khi phân tích dữ liệu: {e}")

    return product


def download_product_images(product):
    """Tải ảnh sản phẩm về thư mục local"""
    if not product or not product.get("images"):
        return

    pid = product.get("product_id", "unknown")
    # Tạo tên thư mục an toàn từ tên sản phẩm
    safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '' for c in (product.get("title", "") or ""))
    safe_title = safe_title[:50].strip()
    folder_name = f"{pid}_{safe_title}" if safe_title else pid

    product_img_dir = os.path.join(IMAGE_FOLDER, folder_name)
    os.makedirs(product_img_dir, exist_ok=True)

    for idx, img_url in enumerate(product["images"]):
        try:
            filename = f"{pid}_img_{idx + 1}.jpg"
            full_path = os.path.join(product_img_dir, filename)

            if os.path.exists(full_path):
                continue

            response = requests.get(img_url, headers=get_random_headers(), stream=True, timeout=20)
            if response.status_code == 200:
                with open(full_path, 'wb') as f:
                    for chunk in response.iter_content(8192):
                        f.write(chunk)
            time.sleep(0.5)

        except Exception as e:
            print(f"   ⚠️ Lỗi tải ảnh {idx + 1}: {e}")


def save_to_csv(products, filename="products.csv"):
    """Lưu danh sách sản phẩm ra file CSV"""
    if not products:
        return

    filepath = os.path.join(BASE_FOLDER, filename)

    fieldnames = [
        "product_id", "title", "price", "original_price", "discount_rate",
        "rating", "review_count", "quantity_sold", "availability", "brand",
        "category", "short_description", "features", "seller",
        "coupons", "badges", "sku", "image_count", "url"
    ]

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for p in products:
            row = {
                **p,
                "features": " | ".join(p.get("features", [])),
                "coupons": " | ".join(p.get("coupons", [])),
                "badges": " | ".join(p.get("badges", [])),
                "image_count": len(p.get("images", [])),
            }
            writer.writerow(row)

    print(f"📄 Đã lưu CSV: {filepath}")


def save_to_json(products, filename="products.json"):
    """Lưu toàn bộ dữ liệu chi tiết ra file JSON"""
    if not products:
        return

    filepath = os.path.join(BASE_FOLDER, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    print(f"📄 Đã lưu JSON: {filepath}")


def main():
    print("=" * 55)
    print("   🛒  TOOL CRAWL DATA SẢN PHẨM TIKI")
    print("=" * 55)

    # Tạo thư mục
    os.makedirs(BASE_FOLDER, exist_ok=True)
    if DOWNLOAD_IMAGES:
        os.makedirs(IMAGE_FOLDER, exist_ok=True)

    all_product_ids = []

    # Trích xuất product ID từ URL
    for url in PRODUCT_URLS:
        pid = extract_product_id(url)
        if pid and pid not in all_product_ids:
            all_product_ids.append(pid)

    # Nếu có từ khóa tìm kiếm, crawl thêm từ kết quả search
    if SEARCH_KEYWORDS:
        for keyword in SEARCH_KEYWORDS:
            found_ids = search_tiki(keyword, MAX_SEARCH_PAGES)
            for pid in found_ids:
                if str(pid) not in [str(x) for x in all_product_ids]:
                    all_product_ids.append(pid)

    if not all_product_ids:
        print("❌ Chưa có sản phẩm nào!")
        print("   → Điền URL vào PRODUCT_URLS hoặc từ khóa vào SEARCH_KEYWORDS")
        return

    print(f"\n📋 Tổng cộng {len(all_product_ids)} sản phẩm cần crawl.")
    print("-" * 55)

    # Crawl chi tiết từng sản phẩm
    all_products = []
    for idx, pid in enumerate(all_product_ids, 1):
        print(f"\n[{idx}/{len(all_product_ids)}] ", end="")
        product = scrape_product_detail(pid)

        if product:
            all_products.append(product)

            # Tải ảnh nếu bật
            if DOWNLOAD_IMAGES and product.get("images"):
                print(f"   🖼️ Đang tải {len(product['images'])} ảnh...")
                download_product_images(product)

        # Lưu dữ liệu sau mỗi 10 sản phẩm (đề phòng lỗi giữa chừng)
        if idx % 10 == 0 and all_products:
            save_to_csv(all_products, "products_temp.csv")
            save_to_json(all_products, "products_temp.json")
            print(f"💾 Đã lưu tạm {len(all_products)} sản phẩm.")

    # Lưu kết quả cuối cùng
    if all_products:
        save_to_csv(all_products)
        save_to_json(all_products)

        # In thống kê
        print(f"\n{'=' * 55}")
        print(f"   ✅ HOÀN THÀNH CRAWL TIKI!")
        print(f"{'=' * 55}")
        print(f"   📦 Tổng sản phẩm crawl được: {len(all_products)}/{len(all_product_ids)}")
        print(f"   📄 File CSV: {os.path.abspath(os.path.join(BASE_FOLDER, 'products.csv'))}")
        print(f"   📄 File JSON: {os.path.abspath(os.path.join(BASE_FOLDER, 'products.json'))}")
        if DOWNLOAD_IMAGES:
            print(f"   🖼️ Thư mục ảnh: {os.path.abspath(IMAGE_FOLDER)}")
        print(f"{'=' * 55}")
    else:
        print("\n❌ Không crawl được sản phẩm nào!")


if __name__ == "__main__":
    main()
