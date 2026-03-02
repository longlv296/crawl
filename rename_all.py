import os

def rename_files_to_image(root_folder):
    # Các định dạng ảnh muốn đổi tên (có thể thêm nếu cần)
    image_extensions = ('.jpg', '.jpeg', '.png', '.webp')
    
    count = 0
    # os.walk sẽ đi xuyên qua tất cả các thư mục con
    for root, dirs, files in os.walk(root_folder):
        for filename in files:
            # Kiểm tra nếu là file ảnh
            if filename.lower().endswith(image_extensions):
                # Không đổi tên nếu file đó đã tên là image.jpg rồi
                if filename.lower() == "image.jpg":
                    continue
                
                old_path = os.path.join(root, filename)
                
                # Lấy phần mở rộng của file gốc (ví dụ .jpg)
                file_ext = os.path.splitext(filename)[1].lower()
                new_name = "image" + file_ext
                new_path = os.path.join(root, new_name)

                try:
                    # Nếu file image.jpg đã tồn tại thì sẽ ghi đè hoặc báo lỗi tùy OS
                    # Ở đây ta dùng rename đơn giản
                    os.rename(old_path, new_path)
                    print(f"Đã đổi: {filename} -> {new_name} (tại {os.path.basename(root)})")
                    count += 1
                except Exception as e:
                    print(f"Lỗi khi đổi file {filename}: {e}")

    print(f"\n--- Hoàn tất! Đã đổi tên tổng cộng {count} file ---")

if __name__ == "__main__":
    # Vì file đặt ở folder 'data', ta quét thư mục 'perenual'
    current_dir = os.path.dirname(os.path.abspath(__file__))
    target_subfolder = os.path.join(current_dir, "perenual")
    
    if os.path.exists(target_subfolder):
        confirm = input(f"Bạn có chắc muốn đổi tên tất cả ảnh trong {target_subfolder} thành 'image.jpg' không? (y/n): ")
        if confirm.lower() == 'y':
            rename_files_to_image(target_subfolder)
    else:
        print(f"Không tìm thấy thư mục: {target_subfolder}")