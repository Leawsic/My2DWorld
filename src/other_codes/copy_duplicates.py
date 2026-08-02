import os
import shutil

def collect_files_by_relpath(root_dir):
    """
    递归遍历 root_dir，返回字典 {相对路径: 绝对路径}
    只收集文件（不包含目录）
    """
    file_map = {}
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:
            abs_path = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(abs_path, root_dir)
            file_map[rel_path] = abs_path
    return file_map

def copy_matching_files(folder_a, folder_b, overwrite=True):
    """
    将 folder_a 中与 folder_b 具有相同相对路径的文件复制到 folder_b，
    覆盖同名文件（若 overwrite=True）。
    """
    # 收集 B 中的所有文件相对路径
    b_files = collect_files_by_relpath(folder_b)
    print(f"B 中共有 {len(b_files)} 个文件")

    # 遍历 A 中的文件
    a_files = collect_files_by_relpath(folder_a)
    print(f"A 中共有 {len(a_files)} 个文件")

    matched = 0
    for rel_path, a_abs in a_files.items():
        if rel_path in b_files:
            dest = os.path.join(folder_b, rel_path)
            # 确保目标目录存在
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            try:
                shutil.copy2(a_abs, dest)  # copy2 保留元数据
                print(f"✓ 已复制: {rel_path}")
                matched += 1
            except Exception as e:
                print(f"✗ 复制 {rel_path} 失败: {e}")
    print(f"共匹配并复制了 {matched} 个文件")

if __name__ == "__main__":
    # 请修改为你的实际路径
    A_folder = r"D:\U盘\texture\Faithful 32x - 26.2\assets\minecraft\textures\block"
    B_folder = r"D:\U盘\texture\F8thful\assets\minecraft\textures\block"
    copy_matching_files(A_folder, B_folder, overwrite=True)
