import os

def dem_thu_muc(duong_dan):
    if not os.path.isdir(duong_dan):
        return "Đường dẫn không hợp lệ hoặc không phải thư mục."

    folders = [f for f in os.listdir(duong_dan) if os.path.isdir(os.path.join(duong_dan, f))]
    
    return len(folders)

thu_muc = r"C:\Users\Welcome\Documents\crawl\data\perenual\species_image"
print(f"Số lượng thư mục: {dem_thu_muc(thu_muc)}")