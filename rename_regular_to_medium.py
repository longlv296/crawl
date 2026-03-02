import os

def rename_regular_to_medium(root_folder):
    count = 0
    # Duyệt qua toàn bộ thư mục perenual
    # topdown=False rất quan trọng khi đổi tên thư mục để tránh lỗi đường dẫn thay đổi
    for root, dirs, files in os.walk(root_folder, topdown=False):
        for name in dirs:
            if name.lower() == "regular":
                old_path = os.path.join(root, name)
                new_path = os.path.join(root, "medium")
                
                try:
                    # Kiểm tra nếu thư mục 'medium' đã tồn tại chưa
                    if not os.path.exists(new_path):
                        os.rename(old_path, new_path)
                        print(f"Đã đổi: {old_path} -> medium")
                        count += 1
                    else:
                        print(f"[Bỏ qua] {root} đã có thư mục medium")
                except Exception as e:
                    print(f"Lỗi tại {old_path}: {e}")

    print(f"\n--- Hoàn tất! Đã đổi tên {count} thư mục ---")

if __name__ == "__main__":
    # Lấy đường dẫn thư mục hiện tại (thư mục 'data')
    current_dir = os.path.dirname(os.path.abspath(__file__))
    target_subfolder = os.path.join(current_dir, "perenual", "species_image")
    
    if os.path.exists(target_subfolder):
        confirm = input(f"Bạn muốn đổi tất cả folder 'regular' thành 'medium' trong {target_subfolder}? (y/n): ")
        if confirm.lower() == 'y':
            rename_regular_to_medium(target_subfolder)
    else:
        print(f"Không tìm thấy thư mục: {target_subfolder}")