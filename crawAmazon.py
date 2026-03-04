import os
import csv
import json
import time
import random
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, quote_plus

# ======================== CẤU HÌNH ========================
BASE_FOLDER = "data_amazon"          # Thư mục gốc lưu dữ liệu
IMAGE_FOLDER = "data_amazon/images"  # Thư mục lưu ảnh sản phẩm

# Danh sách URL sản phẩm Amazon cần crawl
# Ví dụ: https://www.amazon.com/dp/B0XXXXXXXXX
PRODUCT_URLS = [
    # Điền URL sản phẩm vào đây, mỗi URL trên 1 dòng
    # "https://www.amazon.com/dp/B0XXXXXXXXX",
    # "https://www.amazon.com/dp/B0YYYYYYYYY",
]

# HOẶC: Crawl từ trang tìm kiếm theo từ khóa
SEARCH_KEYWORDS = [
    # Điền từ khóa tìm kiếm, mỗi từ khóa trên 1 dòng
    # "wireless headphones",
    # "mechanical keyboard",
    "Dresses","Spring Jackets"
]

# Số trang tìm kiếm tối đa cho mỗi từ khóa (mỗi trang ~20-48 sản phẩm)
MAX_SEARCH_PAGES = 3

# Có tải ảnh sản phẩm về không?
DOWNLOAD_IMAGES = True

# Số luồng tải song song
MAX_WORKERS = 5

# Domain Amazon (đổi nếu cần crawl Amazon khác)
AMAZON_DOMAIN = "https://www.amazon.com"
# ==========================================================

# Headers giả lập trình duyệt thật để tránh bị Amazon chặn
HEADERS_LIST = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
                      "(KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) "
                      "Gecko/20100101 Firefox/121.0",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Connection": "keep-alive",
    },
]


def get_random_headers():
    """Trả về headers ngẫu nhiên để tránh bị phát hiện bot"""
    return random.choice(HEADERS_LIST)


def safe_request(url, max_retries=3):
    """Gửi request với cơ chế retry và delay ngẫu nhiên"""
    for attempt in range(max_retries):
        try:
            # Delay ngẫu nhiên 2-5 giây giữa các request
            delay = random.uniform(2, 5)
            time.sleep(delay)

            response = requests.get(url, headers=get_random_headers(), timeout=20)

            if response.status_code == 200:
                return response
            elif response.status_code == 503:
                # Amazon yêu cầu CAPTCHA, đợi lâu hơn
                print(f"⚠️ Amazon yêu cầu xác minh (503). Đợi 30 giây...")
                time.sleep(30)
            elif response.status_code == 404:
                print(f"❌ Không tìm thấy trang: {url}")
                return None
            else:
                print(f"⚠️ HTTP {response.status_code} - Thử lại ({attempt + 1}/{max_retries})...")
                time.sleep(10)

        except Exception as e:
            print(f"⚠️ Lỗi kết nối ({attempt + 1}/{max_retries}): {e}")
            time.sleep(5)

    print(f"❌ Không thể truy cập sau {max_retries} lần thử: {url[:80]}...")
    return None


def scrape_product_detail(url):
    """Crawl toàn bộ thông tin chi tiết của 1 sản phẩm"""
    print(f"\n🔍 Đang crawl: {url}")

    response = safe_request(url)
    if not response:
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    product = {
        "url": url,
        "asin": "",
        "title": "",
        "price": "",
        "original_price": "",
        "discount": "",
        "rating": "",
        "review_count": "",
        "availability": "",
        "brand": "",
        "category": "",
        "description": "",
        "features": [],
        "specifications": {},
        "images": [],
        "seller": "",
        "best_seller_rank": "",
    }

    try:
        # --- ASIN (mã sản phẩm Amazon) ---
        if "/dp/" in url:
            product["asin"] = url.split("/dp/")[1].split("/")[0].split("?")[0]

        # --- Tên sản phẩm ---
        title_el = soup.find("span", {"id": "productTitle"})
        if title_el:
            product["title"] = title_el.get_text(strip=True)

        # --- Giá hiện tại ---
        price_el = soup.find("span", class_="a-price-whole")
        price_frac = soup.find("span", class_="a-price-fraction")
        if price_el:
            price = price_el.get_text(strip=True).rstrip(".")
            if price_frac:
                price += "." + price_frac.get_text(strip=True)
            product["price"] = price

        # Hoặc tìm giá ở vị trí khác
        if not product["price"]:
            price_box = soup.find("span", {"id": "priceblock_ourprice"}) or \
                        soup.find("span", {"id": "priceblock_dealprice"})
            if price_box:
                product["price"] = price_box.get_text(strip=True)

        # --- Giá gốc (trước giảm giá) ---
        orig_price = soup.find("span", class_="a-price a-text-price")
        if orig_price:
            orig_span = orig_price.find("span", class_="a-offscreen")
            if orig_span:
                product["original_price"] = orig_span.get_text(strip=True)

        # --- Phần trăm giảm giá ---
        discount_el = soup.find("span", class_="savingsPercentage")
        if discount_el:
            product["discount"] = discount_el.get_text(strip=True)

        # --- Đánh giá (rating) ---
        rating_el = soup.find("span", {"id": "acrPopover"})
        if rating_el:
            rating_text = rating_el.get("title", "")
            product["rating"] = rating_text.replace(" out of 5 stars", "").strip()

        # --- Số lượng review ---
        review_el = soup.find("span", {"id": "acrCustomerReviewCount"})
        if review_el:
            product["review_count"] = review_el.get_text(strip=True).split()[0]

        # --- Tình trạng hàng ---
        avail_el = soup.find("div", {"id": "availability"})
        if avail_el:
            product["availability"] = avail_el.get_text(strip=True)

        # --- Thương hiệu ---
        brand_el = soup.find("a", {"id": "bylineInfo"})
        if brand_el:
            product["brand"] = brand_el.get_text(strip=True)
        else:
            brand_row = soup.find("tr", class_="po-brand")
            if brand_row:
                brand_val = brand_row.find("span", class_="po-break-word")
                if brand_val:
                    product["brand"] = brand_val.get_text(strip=True)

        # --- Danh mục (breadcrumb) ---
        breadcrumb = soup.find("div", {"id": "wayfinding-breadcrumbs_container"})
        if breadcrumb:
            links = breadcrumb.find_all("a")
            categories = [a.get_text(strip=True) for a in links]
            product["category"] = " > ".join(categories)

        # --- Mô tả sản phẩm ---
        desc_el = soup.find("div", {"id": "productDescription"})
        if desc_el:
            product["description"] = desc_el.get_text(strip=True)

        # --- Tính năng nổi bật (bullet points) ---
        features_el = soup.find("div", {"id": "feature-bullets"})
        if features_el:
            bullets = features_el.find_all("span", class_="a-list-item")
            product["features"] = [b.get_text(strip=True) for b in bullets if b.get_text(strip=True)]

        # --- Thông số kỹ thuật ---
        spec_table = soup.find("table", {"id": "productDetails_techSpec_section_1"})
        if spec_table:
            rows = spec_table.find_all("tr")
            for row in rows:
                th = row.find("th")
                td = row.find("td")
                if th and td:
                    key = th.get_text(strip=True)
                    value = td.get_text(strip=True)
                    product["specifications"][key] = value

        # Thông số từ bảng khác (Product Information)
        detail_table = soup.find("table", {"id": "productDetails_detailBullets_sections1"})
        if detail_table:
            rows = detail_table.find_all("tr")
            for row in rows:
                th = row.find("th")
                td = row.find("td")
                if th and td:
                    key = th.get_text(strip=True)
                    value = td.get_text(strip=True)
                    product["specifications"][key] = value

        # --- Ảnh sản phẩm ---
        # Tìm ảnh trong thẻ img của gallery
        img_container = soup.find("div", {"id": "imageBlock"}) or \
                        soup.find("div", {"id": "altImages"})
        if img_container:
            imgs = img_container.find_all("img")
            for img in imgs:
                src = img.get("src", "")
                # Chuyển URL thumbnail thành ảnh lớn
                if "images/I/" in src:
                    # Thay đổi kích thước ảnh: thay _SS40_ hoặc _SX/SY... thành _SL1500_
                    import re
                    high_res = re.sub(r'\._[A-Z]{2}\d+_', '._SL1500_', src)
                    if high_res not in product["images"]:
                        product["images"].append(high_res)

        # Tìm ảnh chính
        main_img = soup.find("img", {"id": "landingImage"})
        if main_img:
            src = main_img.get("data-old-hires") or main_img.get("src", "")
            if src and src not in product["images"]:
                product["images"].insert(0, src)

        # --- Người bán ---
        seller_el = soup.find("a", {"id": "sellerProfileTriggerId"})
        if seller_el:
            product["seller"] = seller_el.get_text(strip=True)

        # --- Xếp hạng Best Seller ---
        bsr_el = soup.find("span", string=lambda t: t and "Best Sellers Rank" in t if t else False)
        if bsr_el:
            parent = bsr_el.parent
            if parent:
                product["best_seller_rank"] = parent.get_text(strip=True)

        print(f"✅ Đã crawl: {product['title'][:60] if product['title'] else 'N/A'}...")

    except Exception as e:
        print(f"❌ Lỗi khi phân tích trang: {e}")

    return product


def search_amazon(keyword, max_pages=3):
    """Tìm kiếm sản phẩm trên Amazon và trả về danh sách URL"""
    print(f"\n🔎 Đang tìm kiếm: '{keyword}' (tối đa {max_pages} trang)...")
    product_urls = []

    for page in range(1, max_pages + 1):
        search_url = f"{AMAZON_DOMAIN}/s?k={quote_plus(keyword)}&page={page}"
        print(f"   → Trang {page}/{max_pages}: {search_url}")

        response = safe_request(search_url)
        if not response:
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        # Tìm tất cả sản phẩm trên trang kết quả
        items = soup.find_all("div", {"data-component-type": "s-search-result"})

        if not items:
            print(f"   → Trang {page}: Không tìm thấy sản phẩm. Dừng tìm kiếm.")
            break

        for item in items:
            # Lấy ASIN từ data-asin
            asin = item.get("data-asin", "")
            if asin:
                url = f"{AMAZON_DOMAIN}/dp/{asin}"
                if url not in product_urls:
                    product_urls.append(url)

        print(f"   → Trang {page}: Tìm thấy {len(items)} sản phẩm.")

    print(f"✅ Tổng cộng tìm thấy {len(product_urls)} sản phẩm cho '{keyword}'.")
    return product_urls


def download_product_images(product):
    """Tải ảnh sản phẩm về thư mục local"""
    if not product or not product.get("images"):
        return

    asin = product.get("asin", "unknown")
    # Tạo tên thư mục an toàn từ tên sản phẩm
    safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '' for c in (product.get("title", "") or ""))
    safe_title = safe_title[:50].strip()
    folder_name = f"{asin}_{safe_title}" if safe_title else asin

    product_img_dir = os.path.join(IMAGE_FOLDER, folder_name)
    os.makedirs(product_img_dir, exist_ok=True)

    for idx, img_url in enumerate(product["images"]):
        try:
            filename = f"{asin}_img_{idx + 1}.jpg"
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

    # Các cột cần xuất ra CSV
    fieldnames = [
        "asin", "title", "price", "original_price", "discount",
        "rating", "review_count", "availability", "brand",
        "category", "description", "features", "seller",
        "best_seller_rank", "image_count", "url"
    ]

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for p in products:
            row = {
                **p,
                "features": " | ".join(p.get("features", [])),
                "image_count": len(p.get("images", [])),
            }
            # Bỏ cột images và specifications ra khỏi CSV (lưu riêng JSON)
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
    print("   🛒  TOOL CRAWL DATA SẢN PHẨM AMAZON")
    print("=" * 55)

    # Tạo thư mục
    os.makedirs(BASE_FOLDER, exist_ok=True)
    if DOWNLOAD_IMAGES:
        os.makedirs(IMAGE_FOLDER, exist_ok=True)

    all_product_urls = list(PRODUCT_URLS)  # Copy danh sách URL sản phẩm

    # Nếu có từ khóa tìm kiếm, crawl thêm URL từ kết quả search
    if SEARCH_KEYWORDS:
        for keyword in SEARCH_KEYWORDS:
            found_urls = search_amazon(keyword, MAX_SEARCH_PAGES)
            for url in found_urls:
                if url not in all_product_urls:
                    all_product_urls.append(url)

    if not all_product_urls:
        print("❌ Chưa có URL sản phẩm nào!")
        print("   → Điền URL vào PRODUCT_URLS hoặc từ khóa vào SEARCH_KEYWORDS")
        return

    print(f"\n📋 Tổng cộng {len(all_product_urls)} sản phẩm cần crawl.")
    print("-" * 55)

    # Crawl chi tiết từng sản phẩm
    all_products = []
    for idx, url in enumerate(all_product_urls, 1):
        print(f"\n[{idx}/{len(all_product_urls)}] ", end="")
        product = scrape_product_detail(url)

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
        print(f"   ✅ HOÀN THÀNH CRAWL!")
        print(f"{'=' * 55}")
        print(f"   📦 Tổng sản phẩm crawl được: {len(all_products)}/{len(all_product_urls)}")
        print(f"   📄 File CSV: {os.path.abspath(os.path.join(BASE_FOLDER, 'products.csv'))}")
        print(f"   📄 File JSON: {os.path.abspath(os.path.join(BASE_FOLDER, 'products.json'))}")
        if DOWNLOAD_IMAGES:
            print(f"   🖼️ Thư mục ảnh: {os.path.abspath(IMAGE_FOLDER)}")
        print(f"{'=' * 55}")
    else:
        print("\n❌ Không crawl được sản phẩm nào!")


if __name__ == "__main__":
    main()
