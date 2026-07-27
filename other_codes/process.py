import os
from PIL import Image

def resize_images_inplace(folder_path, scale=0.25):
    """
    将文件夹内所有常见图片（png, jpg, jpeg, bmp, gif）宽高缩放为原来的 scale 倍，
    直接覆盖原文件，不保留备份。
    """
    extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
    
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(extensions):
            file_path = os.path.join(folder_path, filename)
            try:
                with Image.open(file_path) as img:
                    new_size = (int(img.width * scale), int(img.height * scale))
                    resized_img = img.resize(new_size, Image.Resampling.LANCZOS)
                    # 直接保存覆盖原文件（保持原格式）
                    resized_img.save(file_path, quality=95)  # quality 对 JPEG 有效
                    print(f"✓ 已覆盖: {filename} (新尺寸: {new_size[0]}x{new_size[1]})")
            except Exception as e:
                print(f"✗ 处理 {filename} 时出错: {e}")

if __name__ == "__main__":
    # 替换为你的实际图片文件夹路径
    target_folder = r"D:\Project\My2DWorld\assets\textures"
    # 宽高缩放为原来的 1/4
    resize_images_inplace(target_folder, scale=0.25)
