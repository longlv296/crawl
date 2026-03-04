import os

def find_missing_folders(base_path):
    # Kiểm tra xem đường dẫn có tồn tại không
    if not os.path.exists(base_path):
        print(f"❌ Không tìm thấy thư mục: {base_path}")
        return

    print(f"🔍 Đang quét thư mục: {base_path} ...\n")

    existing_ids = set()

    # Quét tất cả các mục trong thư mục
    for item in os.listdir(base_path):
        item_path = os.path.join(base_path, item)
        
        # Chỉ xét các thư mục (bỏ qua file lẻ nếu có)
        if os.path.isdir(item_path):
            # Tách chuỗi theo dấu '_' và lấy phần đầu tiên
            prefix = item.split('_')[0]
            
            # Kiểm tra xem phần đầu có phải là số (ID) không
            if prefix.isdigit():
                existing_ids.add(int(prefix))

    if not existing_ids:
        print("❌ Không tìm thấy folder nào đúng định dạng 'ID_TênCây'.")
        return

    # Tìm ID lớn nhất hiện tại
    max_id = max(existing_ids)
    
    # Tạo một tập hợp (set) chứa tất cả các số từ 1 đến max_id
    full_ids = set(range(1, max_id + 1))
    
    # Dùng phép trừ tập hợp để tìm ra các ID bị thiếu
    missing_ids = sorted(list(full_ids - existing_ids))
    
    # --- IN KẾT QUẢ ---
    print("=== KẾT QUẢ THỐNG KÊ ===")
    print(f"🔹 Folder có ID lớn nhất: {max_id}")
    print(f"🔹 Tổng số folder hợp lệ hiện có: {len(existing_ids)}")
    
    if len(missing_ids) == 0:
        print("\n✅ Tuyệt vời! Bạn đã tải đủ, không thiếu folder nào từ 1 đến", max_id)
    else:
        print(f"\n⚠️ BỊ THIẾU {len(missing_ids)} FOLDER (ID) trong khoảng từ 1 -> {max_id}.")
        print("Danh sách các ID bị thiếu:")
        
        # Nếu danh sách thiếu quá dài, chỉ in 100 ID đầu tiên để tránh trôi màn hình
        if len(missing_ids) > 100:
            print(f"{missing_ids[:100]} \n... (và {len(missing_ids) - 100} ID khác chưa hiển thị)")
            
            # Lưu toàn bộ danh sách thiếu ra file text để bạn dễ theo dõi
            with open("missing_ids.txt", "w") as f:
                f.write(", ".join(map(str, missing_ids)))
            print("\n💾 Đã lưu toàn bộ ID bị thiếu vào file: 'missing_ids.txt'")
        else:
            print(missing_ids)

# Đường dẫn đến thư mục chứa các folder ID (Sửa lại nếu đường dẫn của bạn khác)
# Lưu ý: Trong Python trên Windows, bạn có thể dùng '\\' hoặc '/' đều được.
FOLDER_PATH = "data/perenual/species_image"

if __name__ == "__main__":
    find_missing_folders(FOLDER_PATH)