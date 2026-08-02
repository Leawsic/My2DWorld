from PIL import Image

def make_white_opaque(image_path, output_path):
    """
    将图片中所有不透明像素变为纯白（255,255,255），并将它们全部设为完全不透明（a=255）。
    透明像素（a=0）保持不变。
    """
    img = Image.open(image_path).convert('RGBA')
    # 分离通道
    r, g, b, a = img.split()
    
    # 创建一张纯白图片（尺寸相同）
    white = Image.new('RGB', img.size, (255, 255, 255))
    # 合并：用白色替代RGB，但保留原始Alpha
    # 但如果想强制不透明，可以把Alpha全置为255
    new_alpha = a.point(lambda x: 255 if x > 0 else 0)  # 只要有不透明，就变成255
    result = Image.merge('RGBA', (*white.split(), new_alpha))
    result.save(output_path, 'PNG')
    print(f"已处理: {output_path}")

# 用法
make_white_opaque('backpack.png', 'backpack.png')
