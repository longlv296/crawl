import os
import csv
import json
import time
import random
import requests
import re
from urllib.parse import quote_plus

# ======================== CẤU HÌNH ========================
BASE_FOLDER = "data_shopee"              # Thư mục gốc lưu dữ liệu
IMAGE_FOLDER = "data_shopee/images"      # Thư mục lưu ảnh sản phẩm

# Danh sách URL sản phẩm Shopee cần crawl
# Ví dụ: https://shopee.vn/Ten-san-pham-i.123456.789012
PRODUCT_URLS = [
    # Điền URL sản phẩm vào đây, mỗi URL trên 1 dòng
    # "https://shopee.vn/Ten-san-pham-i.123456.789012",
]

# HOẶC: Crawl từ trang tìm kiếm theo từ khóa
SEARCH_KEYWORDS = [
    # Điền từ khóa tìm kiếm, mỗi từ khóa trên 1 dòng
    # "tai nghe bluetooth",
    # "bàn phím cơ",
    "điện thoại samsung",
]

# Số trang tìm kiếm tối đa cho mỗi từ khóa (mỗi trang ~60 sản phẩm)
MAX_SEARCH_PAGES = 3

# Có tải ảnh sản phẩm về không?
DOWNLOAD_IMAGES = True

# Số luồng tải ảnh song song
MAX_WORKERS = 5

# API Endpoints
SHOPEE_SEARCH_API = "https://shopee.vn/api/v4/search/search_items"
SHOPEE_ITEM_API = "https://shopee.vn/api/v4/item/get"
SHOPEE_SHOP_API = "https://shopee.vn/api/v4/shop/get_shop_detail"

# Image CDN
SHOPEE_IMAGE_CDN = "https://down-vn.img.susercontent.com/file/"
# ==========================================================

# Headers giả lập trình duyệt thật - Shopee yêu cầu headers đặc biệt
HEADERS_LIST = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://shopee.vn/",
        "x-shopee-language": "vi",
        "x-requested-with": "XMLHttpRequest",
        "x-api-source": "pc",
        "Connection": "keep-alive",
        "If-None-Match-": "55b03-e587b77e64dc5",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
                      "(KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
        "Accept": "application/json",
        "Accept-Language": "vi-VN,vi;q=0.9",
        "Referer": "https://shopee.vn/",
        "x-shopee-language": "vi",
        "x-requested-with": "XMLHttpRequest",
        "x-api-source": "pc",
        "Connection": "keep-alive",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) "
                      "Gecko/20100101 Firefox/121.0",
        "Accept": "application/json",
        "Accept-Language": "vi-VN,vi;q=0.5",
        "Referer": "https://shopee.vn/",
        "x-shopee-language": "vi",
        "x-requested-with": "XMLHttpRequest",
        "x-api-source": "pc",
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
            # Delay ngẫu nhiên 3-7 giây (Shopee anti-bot mạnh hơn)
            delay = random.uniform(3, 7)
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
                print(f"⚠️ Shopee rate limit (429). Đợi 60 giây...")
                time.sleep(60)
            elif response.status_code == 403:
                print(f"⚠️ Shopee chặn request (403). Đợi 30 giây...")
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


def extract_shop_item_id(url):
    """Trích xuất shop_id và item_id từ URL Shopee"""
    # Pattern: https://shopee.vn/Ten-san-pham-i.123456.789012
    match = re.search(r'-i\.(\d+)\.(\d+)', url)
    if match:
        return int(match.group(1)), int(match.group(2))

    # Pattern: https://shopee.vn/product/123456/789012
    match = re.search(r'/product/(\d+)/(\d+)', url)
    if match:
        return int(match.group(1)), int(match.group(2))

    return None, None


def get_image_url(image_hash):
    """Chuyển image hash thành URL đầy đủ"""
    if not image_hash:
        return ""
    if image_hash.startswith("http"):
        return image_hash
    return f"{SHOPEE_IMAGE_CDN}{image_hash}"


def format_price(price):
    """Chuyển đổi giá từ đơn vị Shopee (x100000) sang VNĐ"""
    if not price:
        return ""
    try:
        # Shopee lưu giá nhân 100000
        real_price = int(price) / 100000
        return f"{real_price:,.0f}"
    except (ValueError, TypeError):
        return str(price)


def search_shopee(keyword, max_pages=3):
    """Tìm kiếm sản phẩm trên Shopee và trả về danh sách (shop_id, item_id)"""
    print(f"\n🔎 Đang tìm kiếm trên Shopee: '{keyword}' (tối đa {max_pages} trang)...")
    product_pairs = []  # List of (shop_id, item_id)

    for page in range(max_pages):
        params = {
            "by": "relevancy",
            "keyword": keyword,
            "limit": 60,
            "newest": page * 60,
            "order": "desc",
            "page_type": "search",
            "scenario": "PAGE_GLOBAL_SEARCH",
            "version": 2,
        }

        print(f"   → Trang {page + 1}/{max_pages}...")

        response = safe_request(SHOPEE_SEARCH_API, params=params)
        if not response:
            continue

        try:
            data = response.json()

            # Kiểm tra có lỗi không
            if data.get("error"):
                error_code = data.get("error")
                if error_code != 0:
                    print(f"   ⚠️ Shopee API error: {data.get('error_msg', error_code)}")
                    # Nếu bị anti-bot, dừng lại
                    if "anti" in str(data.get("error_msg", "")).lower():
                        print("   ⚠️ Phát hiện anti-bot. Dừng tìm kiếm.")
                        break

            items = data.get("items", [])

            if not items:
                print(f"   → Trang {page + 1}: Không tìm thấy sản phẩm. Dừng tìm kiếm.")
                break

            for item in items:
                item_basic = item.get("item_basic", {})
                shop_id = item_basic.get("shopid")
                item_id = item_basic.get("itemid")
                if shop_id and item_id:
                    pair = (shop_id, item_id)
                    if pair not in product_pairs:
                        product_pairs.append(pair)

            print(f"   → Trang {page + 1}: Tìm thấy {len(items)} sản phẩm.")

        except Exception as e:
            print(f"   ⚠️ Lỗi phân tích JSON trang {page + 1}: {e}")

    print(f"✅ Tổng cộng tìm thấy {len(product_pairs)} sản phẩm cho '{keyword}'.")
    return product_pairs


def scrape_product_detail(shop_id, item_id):
    """Crawl toàn bộ thông tin chi tiết của 1 sản phẩm từ API Shopee"""
    print(f"\n🔍 Đang crawl sản phẩm: shop={shop_id}, item={item_id}")

    params = {
        "itemid": item_id,
        "shopid": shop_id,
    }

    response = safe_request(SHOPEE_ITEM_API, params=params)
    if not response:
        return None

    try:
        result = response.json()
        data = result.get("data", {})
        if not data:
            print(f"❌ Không có dữ liệu sản phẩm")
            return None
    except Exception as e:
        print(f"❌ Lỗi phân tích JSON: {e}")
        return None

    product = {
        "item_id": str(item_id),
        "shop_id": str(shop_id),
        "url": f"https://shopee.vn/product/{shop_id}/{item_id}",
        "title": "",
        "price": "",
        "price_min": "",
        "price_max": "",
        "original_price": "",
        "discount": "",
        "rating": "",
        "rating_count": [],
        "review_count": "",
        "quantity_sold": "",
        "stock": "",
        "brand": "",
        "category": "",
        "category_id": "",
        "description": "",
        "attributes": {},
        "images": [],
        "video_url": "",
        "thumbnail": "",
        "shop_name": "",
        "shop_rating": "",
        "shop_location": "",
        "shop_response_rate": "",
        "shop_response_time": "",
        "vouchers": [],
        "flash_sale": "",
        "is_official_shop": False,
        "is_preferred_plus": False,
        "liked_count": "",
        "view_count": "",
        "tier_variations": [],
        "status": "",
    }

    try:
        # --- Tên sản phẩm ---
        product["title"] = data.get("name", "")

        # --- Giá ---
        product["price"] = format_price(data.get("price"))
        product["price_min"] = format_price(data.get("price_min"))
        product["price_max"] = format_price(data.get("price_max"))

        # --- Giá gốc ---
        product["original_price"] = format_price(data.get("price_before_discount"))

        # --- Giảm giá ---
        discount = data.get("raw_discount", 0) or data.get("discount", 0)
        if discount:
            product["discount"] = f"-{discount}%"
        elif data.get("show_discount"):
            product["discount"] = f"-{data.get('show_discount')}%"

        # --- Đánh giá (rating) ---
        rating = data.get("item_rating", {})
        if isinstance(rating, dict):
            product["rating"] = str(round(rating.get("rating_star", 0), 1))
            rating_count = rating.get("rating_count", [])
            product["rating_count"] = rating_count
            # Tổng số đánh giá (index 0 = tổng)
            if rating_count:
                product["review_count"] = str(rating_count[0])

        # --- Số lượng đã bán ---
        sold = data.get("historical_sold", 0) or data.get("sold", 0)
        product["quantity_sold"] = str(sold)

        # --- Tồn kho ---
        product["stock"] = str(data.get("stock", ""))

        # --- Thương hiệu ---
        product["brand"] = data.get("brand", "") or ""

        # --- Danh mục ---
        categories = data.get("categories", [])
        if categories:
            cat_names = [c.get("display_name", "") for c in categories if c.get("display_name")]
            product["category"] = " > ".join(cat_names)
        cat_id = data.get("catid", "")
        product["category_id"] = str(cat_id)

        # --- Mô tả ---
        product["description"] = data.get("description", "")

        # --- Thuộc tính sản phẩm ---
        attributes = data.get("attributes", [])
        if attributes:
            for attr in attributes:
                attr_name = attr.get("name", "")
                attr_value = attr.get("value", "")
                if attr_name and attr_value:
                    product["attributes"][attr_name] = attr_value

        # --- Ảnh sản phẩm ---
        images = data.get("images", [])
        if images:
            for img_hash in images:
                img_url = get_image_url(img_hash)
                if img_url and img_url not in product["images"]:
                    product["images"].append(img_url)

        # Thumbnail
        thumbnail = data.get("image", "")
        if thumbnail:
            product["thumbnail"] = get_image_url(thumbnail)

        # --- Video ---
        video_info = data.get("video_info_list", [])
        if video_info:
            for vid in video_info:
                video_url = vid.get("default_format", {}).get("url", "")
                if video_url:
                    product["video_url"] = video_url
                    break

        # --- Thông tin Shop ---
        shop_info = data.get("shop_info", {}) or data.get("shopee_verified", {})
        if isinstance(shop_info, dict):
            product["shop_name"] = shop_info.get("shop_name", "") or shop_info.get("username", "")
            product["shop_rating"] = str(shop_info.get("shop_rating", ""))
            product["shop_location"] = shop_info.get("shop_location", "")
            product["shop_response_rate"] = str(shop_info.get("response_rate", ""))
            product["shop_response_time"] = str(shop_info.get("response_time", ""))

        # --- Voucher / Mã giảm giá ---
        vouchers = data.get("voucher_info", {})
        if isinstance(vouchers, dict):
            promotion_id = vouchers.get("promotion_id", "")
            voucher_code = vouchers.get("voucher_code", "")
            label = vouchers.get("label", "")
            if label:
                product["vouchers"].append(label)
            elif voucher_code:
                product["vouchers"].append(voucher_code)

        # Shop voucher
        shop_vouchers = data.get("shop_vouchers", [])
        if shop_vouchers:
            for sv in shop_vouchers:
                if isinstance(sv, dict):
                    v_label = sv.get("label", "") or sv.get("title", "")
                    if v_label:
                        product["vouchers"].append(v_label)

        # --- Flash Sale ---
        flash_sale = data.get("flash_sale", {})
        if isinstance(flash_sale, dict) and flash_sale:
            product["flash_sale"] = f"Flash Sale - Giá: {format_price(flash_sale.get('price', ''))}"

        upcoming_flash_sale = data.get("upcoming_flash_sale", {})
        if isinstance(upcoming_flash_sale, dict) and upcoming_flash_sale:
            product["flash_sale"] = f"Upcoming Flash Sale - Giá: {format_price(upcoming_flash_sale.get('price', ''))}"

        # --- Badges ---
        product["is_official_shop"] = bool(data.get("shopee_verified", False) or data.get("is_official_shop", False))
        product["is_preferred_plus"] = bool(data.get("show_shopee_verified_label", False))

        # --- Tương tác ---
        product["liked_count"] = str(data.get("liked_count", ""))
        product["view_count"] = str(data.get("view_count", ""))

        # --- Phân loại hàng (biến thể: size, màu...) ---
        tier_variations = data.get("tier_variations", [])
        if tier_variations:
            for tv in tier_variations:
                var_name = tv.get("name", "")
                var_options = tv.get("options", [])
                if var_name and var_options:
                    product["tier_variations"].append({
                        "name": var_name,
                        "options": var_options
                    })

        # --- Trạng thái ---
        product["status"] = data.get("status", "")

        print(f"✅ Đã crawl: {product['title'][:60] if product['title'] else 'N/A'}...")

    except Exception as e:
        print(f"❌ Lỗi khi phân tích dữ liệu: {e}")

    return product


def download_product_images(product):
    """Tải ảnh sản phẩm về thư mục local"""
    if not product or not product.get("images"):
        return

    item_id = product.get("item_id", "unknown")
    # Tạo tên thư mục an toàn từ tên sản phẩm
    safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '' for c in (product.get("title", "") or ""))
    safe_title = safe_title[:50].strip()
    folder_name = f"{item_id}_{safe_title}" if safe_title else item_id

    product_img_dir = os.path.join(IMAGE_FOLDER, folder_name)
    os.makedirs(product_img_dir, exist_ok=True)

    for idx, img_url in enumerate(product["images"]):
        try:
            filename = f"{item_id}_img_{idx + 1}.jpg"
            full_path = os.path.join(product_img_dir, filename)

            if os.path.exists(full_path):
                continue

            response = requests.get(img_url, stream=True, timeout=20)
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
        "item_id", "title", "price", "price_min", "price_max",
        "original_price", "discount", "rating", "review_count",
        "quantity_sold", "stock", "brand", "category",
        "description", "shop_name", "shop_location", "shop_rating",
        "vouchers", "flash_sale", "is_official_shop",
        "liked_count", "view_count", "tier_variations",
        "image_count", "url"
    ]

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for p in products:
            row = {
                **p,
                "vouchers": " | ".join(p.get("vouchers", [])),
                "tier_variations": json.dumps(p.get("tier_variations", []), ensure_ascii=False),
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
    print("   🛒  TOOL CRAWL DATA SẢN PHẨM SHOPEE")
    print("=" * 55)
    print("   ⚠️  Lưu ý: Shopee có anti-bot mạnh.")
    print("   ⚠️  Nếu bị block, hãy tăng delay hoặc đợi 1-2 phút.")
    print("=" * 55)

    # Tạo thư mục
    os.makedirs(BASE_FOLDER, exist_ok=True)
    if DOWNLOAD_IMAGES:
        os.makedirs(IMAGE_FOLDER, exist_ok=True)

    all_product_pairs = []  # List of (shop_id, item_id)

    # Trích xuất shop_id và item_id từ URL
    for url in PRODUCT_URLS:
        shop_id, item_id = extract_shop_item_id(url)
        if shop_id and item_id:
            pair = (shop_id, item_id)
            if pair not in all_product_pairs:
                all_product_pairs.append(pair)

    # Nếu có từ khóa tìm kiếm, crawl thêm từ kết quả search
    if SEARCH_KEYWORDS:
        for keyword in SEARCH_KEYWORDS:
            found_pairs = search_shopee(keyword, MAX_SEARCH_PAGES)
            for pair in found_pairs:
                if pair not in all_product_pairs:
                    all_product_pairs.append(pair)

    if not all_product_pairs:
        print("❌ Chưa có sản phẩm nào!")
        print("   → Điền URL vào PRODUCT_URLS hoặc từ khóa vào SEARCH_KEYWORDS")
        return

    print(f"\n📋 Tổng cộng {len(all_product_pairs)} sản phẩm cần crawl.")
    print("-" * 55)

    # Crawl chi tiết từng sản phẩm
    all_products = []
    for idx, (shop_id, item_id) in enumerate(all_product_pairs, 1):
        print(f"\n[{idx}/{len(all_product_pairs)}] ", end="")
        product = scrape_product_detail(shop_id, item_id)

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
        print(f"   ✅ HOÀN THÀNH CRAWL SHOPEE!")
        print(f"{'=' * 55}")
        print(f"   📦 Tổng sản phẩm crawl được: {len(all_products)}/{len(all_product_pairs)}")
        print(f"   📄 File CSV: {os.path.abspath(os.path.join(BASE_FOLDER, 'products.csv'))}")
        print(f"   📄 File JSON: {os.path.abspath(os.path.join(BASE_FOLDER, 'products.json'))}")
        if DOWNLOAD_IMAGES:
            print(f"   🖼️ Thư mục ảnh: {os.path.abspath(IMAGE_FOLDER)}")
        print(f"{'=' * 55}")
    else:
        print("\n❌ Không crawl được sản phẩm nào!")


if __name__ == "__main__":
    main()
