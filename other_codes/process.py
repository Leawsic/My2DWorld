import os
from PIL import Image

def resize_images_inplace(root_folder, scale=0.25):
    """
    递归地将 root_folder 下所有子文件夹内的常见图片宽高缩放为原来的 scale 倍，
    直接覆盖原文件，不保留备份。
    """
    extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
    
    for dirpath, _, filenames in os.walk(root_folder):
        for filename in filenames:
            if filename.lower().endswith(extensions):
                file_path = os.path.join(dirpath, filename)
                try:
                    with Image.open(file_path) as img:
                        new_size = (int(img.width * scale), int(img.height * scale))
                        resized_img = img.resize(new_size, Image.Resampling.LANCZOS)
                        resized_img.save(file_path, quality=95)  # quality 对 JPEG 有效
                        print(f"✓ 已覆盖: {file_path} (新尺寸: {new_size[0]}x{new_size[1]})")
                except Exception as e:
                    print(f"✗ 处理 {file_path} 时出错: {e}")

if __name__ == "__main__":
    target_folder = r"D:\Project\My2DWorld\assets\textures"# 替换为你的实际图片文件夹路径
    resize_images_inplace(target_folder, scale=0.25)
